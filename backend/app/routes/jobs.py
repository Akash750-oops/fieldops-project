from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json
import uuid
import logging

from app.database import get_db
from app.models import Job, Technician
from app.schemas import JobCreate, JobResponse, PlanResponse, RankedTechnician, DisqualifiedTechnician, ScoringWeights
from app.redis_client import get_redis_client
from app.services.certification_validator import CertificationValidator
from app.services.distance import DistanceScoringService
from app.services.skill import SkillScoringService
from app.services.workload import WorkloadScoringService
from app.services.composite import CompositeScoringService
from app.routes.dispatch import verify_jwt_token

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


@router.post("/", response_model=JobResponse, status_code=201)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    try:
        new_job = Job(
            customer_name=job.customer_name,
            location=job.location,
            issue_description=job.issue_description,
            priority=job.priority,
            service_type=job.service_type,
            contact_number=job.contact_number,
            preferred_service_date=job.preferred_service_date,
            status=job.status,
        )

        db.add(new_job)
        db.commit()
        db.refresh(new_job)

        return new_job

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job: {str(error)}"
        )


@router.get("/", response_model=list[JobResponse])
def get_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.id.desc()).all()

@router.put("/{job_id}", response_model=JobResponse)
def update_job(job_id: int, job: JobCreate, db: Session = Depends(get_db)):
    existing_job = db.query(Job).filter(Job.id == job_id).first()

    if not existing_job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing_job.customer_name = job.customer_name
    existing_job.location = job.location
    existing_job.issue_description = job.issue_description
    existing_job.priority = job.priority
    existing_job.service_type = job.service_type
    existing_job.contact_number = job.contact_number
    existing_job.preferred_service_date = job.preferred_service_date
    existing_job.status = job.status

    db.commit()aa
    db.refresh(existing_job)

    return existing_job

@router.post("/{job_id}/plan", response_model=PlanResponse)
async def plan_job_assignment(
    job_id: int,
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    log_extra = {"correlation_id": correlation_id, "tenant_id": x_tenant_id, "job_id": job_id}
    
    # Rate limit check (max 10 requests per minute)
    rate_limit_key = f"rate_limit:job_plan:{x_tenant_id}:{job_id}"
    req_count = redis_client.incr(rate_limit_key)
    if req_count == 1:
        redis_client.expire(rate_limit_key, 60)
    if req_count > 10:
        logger.warning("Rate limit exceeded for job plan", extra=log_extra)
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Cache check (30s TTL)
    cache_key = f"cache:job_plan:{x_tenant_id}:{job_id}"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        logger.info("Cache hit for job plan", extra=log_extra)
        return json.loads(cached_data)
        
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status.upper() not in ["QUEUED", "ACTIVE"]:
        raise HTTPException(status_code=400, detail="Job must be in QUEUED status to generate a plan")
        
    technicians = db.query(Technician).filter(
        (Technician.tenant_id == x_tenant_id) | (Technician.tenant_id.is_(None)),
        Technician.technician_status == "AVAILABLE"
    ).all()
    
    if not technicians:
        return PlanResponse(
            job_id=str(job_id),
            job_title=f"{job.service_type} - {job.location}",
            status=job.status,
            ranked_technicians=[],
            disqualified_technicians=[],
            scoring_weights=ScoringWeights(proximity=0.4, skill=0.4, workload=0.2),
            generated_at=datetime.now(timezone.utc),
            cache_ttl_seconds=30
        )
        
    validator = CertificationValidator()
    distance_service = DistanceScoringService()
    skill_service = SkillScoringService()
    workload_service = WorkloadScoringService()
    composite_service = CompositeScoringService()
    
    disqualified = []
    qualified = []
    
    job_lat, job_lng = 0.0, 0.0 
    try:
        if "," in job.location:
            parts = job.location.split(",")
            job_lat, job_lng = float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        pass
        
    for tech in technicians:
        # 1. Hard Constraints
        cert_res = validator.validate_certifications(job, tech, db)
        if not cert_res.get("qualified"):
            disq = DisqualifiedTechnician(
                tech_id=tech.tech_id or str(tech.technician_id),
                name=tech.technician_name,
                reason=cert_res.get("reason", "unknown"),
                details=cert_res.get("details", []),
                message=cert_res.get("message", "Disqualified")
            )
            disqualified.append(disq)
            validator.log_disqualification(db, job_id, tech, cert_res)
            continue
            
        # 2. Scoring
        skill_score = skill_service.calculate_skill_score(job.required_skill or "", tech.technician_skill or "", db)
        workload_res = workload_service.calculate_workload_score(db, tech.technician_id, 3)
        if workload_res["score"] == 0.0 and workload_res["active_jobs"] >= 3:
            disq = DisqualifiedTechnician(
                tech_id=tech.tech_id or str(tech.technician_id),
                name=tech.technician_name,
                reason="max_capacity_reached",
                message=f"Technician has reached maximum active jobs ({workload_res['active_jobs']}/3)"
            )
            disqualified.append(disq)
            continue
            
        tech_lat, tech_lng = 0.0, 0.0
        try:
            if "," in tech.technician_location:
                parts = tech.technician_location.split(",")
                tech_lat, tech_lng = float(parts[0].strip()), float(parts[1].strip())
        except ValueError:
            pass
            
        dist_res = await distance_service.calculate_distance_score(
            {"lat": job_lat, "lng": job_lng},
            [{"id": tech.technician_id, "lat": tech_lat, "lng": tech_lng}],
            redis_client
        )
        dist_score = 0.0
        dist_km = None
        if dist_res:
            dist_score = dist_res[0]["score"]
            dist_km = dist_res[0]["distance_km"]
            
        qualified.append({
            "tech_id": tech.tech_id or str(tech.technician_id),
            "name": tech.technician_name,
            "proximity_score": dist_score,
            "skill_score": skill_score,
            "workload_score": workload_res["score"],
            "distance_km": dist_km,
            "active_jobs": workload_res["active_jobs"]
        })
        
    db.commit() 
    
    # 3. Composite Ranking
    weights = composite_service.get_weights(db, x_tenant_id)
    for q in qualified:
        comp = composite_service.composite_score(q["proximity_score"], q["skill_score"], q["workload_score"], weights)
        q["composite_score"] = comp["composite_score"]
        
    ranked = composite_service.rank_technicians(qualified)
    
    ranked_results = []
    for i, r in enumerate(ranked):
        rt = RankedTechnician(
            rank=i + 1,
            tech_id=r["tech_id"],
            name=r["name"],
            proximity_score=r["proximity_score"],
            skill_score=r["skill_score"],
            workload_score=r["workload_score"],
            composite_score=r["composite_score"],
            distance_km=r["distance_km"],
            active_jobs=r["active_jobs"],
            max_capacity=3,
            is_top_3=i < 3,
            is_recommended=i < 3
        )
        ranked_results.append(rt)
        
    res = PlanResponse(
        job_id=str(job_id),
        job_title=f"{job.service_type} - {job.location}",
        status=job.status,
        ranked_technicians=ranked_results,
        disqualified_technicians=disqualified,
        scoring_weights=ScoringWeights(proximity=weights["proximity"], skill=weights["skill"], workload=weights["workload"]),
        generated_at=datetime.now(timezone.utc),
        cache_ttl_seconds=30
    )
    
    res_dict = res.model_dump(mode='json')
    redis_client.setex(cache_key, 30, json.dumps(res_dict))
    
    return res