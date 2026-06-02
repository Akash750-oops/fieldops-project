from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json
import uuid
import logging

from app.database import get_db
from app.models import Job, Technician, AuditEvent, DispatcherNotification
from app.schemas import JobCreate, JobResponse, PlanResponse, RankedTechnician, DisqualifiedTechnician, ScoringWeights
from pydantic import BaseModel, Field
from app.services.distributed_lock_service import with_job_lock
from app.redis_client import get_redis_client
from app.services.certification_validator import CertificationValidator
from app.services.distance import DistanceScoringService
from app.services.cooldown_service import CooldownService
from app.services.exclusion_service import ExclusionService
from app.services.skill import SkillScoringService
from app.services.workload import WorkloadScoringService
from app.services.composite import CompositeScoringService
from app.routes.dispatch import verify_jwt_token

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


@router.get("/stats")
def get_jobs_stats(db: Session = Depends(get_db)):
    try:
        # Total Jobs
        total_jobs = db.query(Job).count()

        # Jobs counts by status
        completed_count = db.query(Job).filter(func.lower(Job.status) == "completed").count()
        in_progress_count = db.query(Job).filter(func.lower(Job.status) == "in progress").count()
        active_count = db.query(Job).filter(func.lower(Job.status) == "active", Job.assigned_technician_id.isnot(None)).count()
        pending_count = db.query(Job).filter(func.lower(Job.status) == "active", Job.assigned_technician_id.is_(None)).count()

        # Technician availability counts
        tech_available = db.query(Technician).filter(func.lower(Technician.technician_status) == "available").count()
        tech_busy = db.query(Technician).filter(
            (func.lower(Technician.technician_status) == "busy") | 
            (func.lower(Technician.technician_status) == "on job") | 
            (func.lower(Technician.technician_status) == "on job / busy")
        ).count()
        tech_break = db.query(Technician).filter(func.lower(Technician.technician_status) == "break").count()
        tech_offline = db.query(Technician).filter(func.lower(Technician.technician_status) == "offline").count()

        # Category splits based on service type
        hvac_count = db.query(Job).filter(func.lower(Job.service_type).like("%hvac%")).count()
        electrical_count = db.query(Job).filter(func.lower(Job.service_type).like("%elec%")).count()
        plumbing_count = db.query(Job).filter(func.lower(Job.service_type).like("%plumb%")).count()
        mechanical_count = db.query(Job).filter(func.lower(Job.service_type).like("%mech%")).count()
        other_count = total_jobs - (hvac_count + electrical_count + plumbing_count + mechanical_count)
        if other_count < 0:
            other_count = 0

        return {
            "jobs": {
                "total": total_jobs,
                "active": active_count,
                "in_progress": in_progress_count,
                "completed": completed_count,
                "pending": pending_count
            },
            "technicians": {
                "available": tech_available,
                "busy": tech_busy,
                "break": tech_break,
                "offline": tech_offline
            },
            "categories": {
                "hvac": hvac_count,
                "electrical": electrical_count,
                "plumbing": plumbing_count,
                "mechanical": mechanical_count,
                "other": other_count
            }
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch dashboard stats: {str(error)}"
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

@router.get("/pending", response_model=list[JobResponse])
def get_pending_jobs(db: Session = Depends(get_db)):
    """
    Retrieve all unassigned/pending jobs.
    """
    try:
        return db.query(Job).filter(Job.assigned_technician_id.is_(None)).order_by(Job.id.desc()).all()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pending jobs: {str(error)}"
        )

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

    db.commit()
    db.refresh(existing_job)

    return existing_job

@router.post("/{job_id}/plan", response_model=PlanResponse)
async def plan_job_assignment(
    job_id: int,
    request: Request,
    admin_override: bool = False,
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
    if req_count is not None:
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
        warnings_list = []
        if admin_override:
            # Check pseudo-JWT for admin/dispatcher roles
            if "admin" not in authorization.lower() and "dispatcher" not in authorization.lower():
                raise HTTPException(status_code=403, detail="Admin or Dispatcher role required for override")
            # Bypass certification logic, just log the override
            audit = AuditEvent(
                tech_id=tech.tech_id or f"id-{tech.technician_id}",
                tenant_id=x_tenant_id,
                event_type="CERT_OVERRIDE",
                old_status="DISQUALIFIED_POTENTIAL",
                new_status="OVERRIDDEN"
            )
            db.add(audit)
            warnings_list.append("Certification constraints bypassed via Admin Override")
        else:
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
            if cert_res.get("warnings"):
                warnings_list.extend(cert_res["warnings"])
                
        if CooldownService.check_cooldown(redis_client, str(job_id), tech.tech_id):
            disq = DisqualifiedTechnician(
                tech_id=tech.tech_id or str(tech.technician_id),
                name=tech.technician_name,
                reason="cooldown_active",
                message="Technician is in cooldown period"
            )
            disqualified.append(disq)
            continue
            
        exc = ExclusionService.is_excluded(redis_client, str(job_id), tech.tech_id)
        if exc.get("excluded"):
            disq = DisqualifiedTechnician(
                tech_id=tech.tech_id or str(tech.technician_id),
                name=tech.technician_name,
                reason=exc.get("reason", "excluded"),
                message="Technician is excluded"
            )
            disqualified.append(disq)
            continue
            
        # 2. Scoring
        skill_res = skill_service.calculate_skill_score(job.required_skill or "", tech.technician_skill or "", db)
        if not skill_res.get("qualified"):
            disq = DisqualifiedTechnician(
                tech_id=tech.tech_id or str(tech.technician_id),
                name=tech.technician_name,
                reason="missing_prerequisite",
                message=skill_res.get("reason", "Missing required skills")
            )
            disqualified.append(disq)
            continue
            
        skill_score = skill_res["score"]
        
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
            "active_jobs": workload_res["active_jobs"],
            "warnings": warnings_list
        })
        
    db.commit() 
    
    # 3. Composite Ranking
    weights = composite_service.get_weights(db, x_tenant_id)
    for q in qualified:
        comp = composite_service.composite_score(q["proximity_score"], q["skill_score"], q["workload_score"], weights)
        q["composite_score"] = comp["composite_score"]
        q["score_breakdown"] = comp["breakdown"]
        
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
            score_breakdown=r.get("score_breakdown"),
            warnings=r.get("warnings"),
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

class JobRejectRequest(BaseModel):
    reason: str = Field(..., min_length=10)

class JobReassignRequest(BaseModel):
    new_tech_id: str
    reason: str

class JobAssignRequest(BaseModel):
    tech_id: str
    justification: str = Field(..., min_length=20)
    skip_skill_check: bool = False
    skip_workload_check: bool = False

@router.post("/{job_id}/accept")
def accept_job(
    job_id: int,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    tech_id = authorization
    lock_key = f"lock:job_accept:{job_id}"
    if not redis_client.set(lock_key, "locked", nx=True, ex=10):
        raise HTTPException(status_code=409, detail="Concurrent modification")
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != "ASSIGNED":
            raise HTTPException(status_code=400, detail="Job is not in ASSIGNED status")
            
        tech = db.query(Technician).filter(Technician.tech_id == tech_id).first()
        if not tech or job.assigned_technician_id != tech.technician_id:
            raise HTTPException(status_code=403, detail="Technician not assigned to this job")
            
        if not redis_client.exists(f"job:timer:{job_id}"):
            raise HTTPException(status_code=423, detail="Acceptance window expired")
            
        job.status = "EN_ROUTE"
        tech.technician_status = "EN_ROUTE"
        tech.current_jobs = 1
        
        audit = AuditEvent(tech_id=tech_id, tenant_id=x_tenant_id, event_type="JOB_ACCEPTED", new_status="EN_ROUTE")
        db.add(audit)
        db.commit()
        
        redis_client.delete(f"job:timer:{job_id}")
        
        return {
            "status": "EN_ROUTE",
            "previous_status": "ASSIGNED",
            "technician": {"tech_id": tech_id, "status": "EN_ROUTE"},
            "tracking_enabled": True
        }
    finally:
        redis_client.delete(lock_key)

@router.post("/{job_id}/reject")
def reject_job(
    job_id: int,
    req: JobRejectRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    tech_id = authorization
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    tech = db.query(Technician).filter(Technician.tech_id == tech_id).first()
    if not tech or job.assigned_technician_id != tech.technician_id:
        raise HTTPException(status_code=403, detail="Technician not assigned to this job")
        
    tech.technician_status = "AVAILABLE"
    tech.current_jobs = 0
    
    from app.services.re_dispatch_queue import ReDispatchQueueService
    ReDispatchQueueService.enqueue_failed_job(
        db=db,
        redis_client=redis_client,
        job=job,
        tenant_id=x_tenant_id,
        reason=req.reason,
        tech_id=tech_id
    )
    
    from app.services.cooldown_service import CooldownService
    CooldownService.set_cooldown(redis_client, str(job.id), tech_id, 120)
    
    audit = AuditEvent(tech_id=tech_id, tenant_id=x_tenant_id, event_type="JOB_REJECTED", new_status="QUEUED", reason=req.reason)
    db.add(audit)
    
    notif = DispatcherNotification(tech_id=tech_id, tenant_id=x_tenant_id, message=f"Rejected: {req.reason}")
    db.add(notif)
    
    db.commit()
    
    return {
        "status": "QUEUED",
        "rejection": {"reason": req.reason},
        "cooldown": {"duration_seconds": 120},
        "re_dispatch": {"triggered": True}
    }

@router.post("/{job_id}/reassign")
def reassign_job(
    job_id: int,
    req: JobReassignRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    tech_id = authorization
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    old_tech = db.query(Technician).filter(Technician.tech_id == tech_id).first()
    if not old_tech or job.assigned_technician_id != old_tech.technician_id:
        raise HTTPException(status_code=403, detail="Technician not assigned to this job")
        
    new_tech = db.query(Technician).filter(Technician.tech_id == req.new_tech_id).first()
    if not new_tech:
        raise HTTPException(status_code=400, detail="New technician not found")
        
    if new_tech.technician_status == "OFFLINE":
        raise HTTPException(status_code=400, detail="New technician is OFFLINE")
        
    if job.required_skill and job.required_skill not in new_tech.technician_skill:
        raise HTTPException(status_code=400, detail="New technician missing required skills")
        
    if new_tech.current_jobs >= 3:
        raise HTTPException(status_code=400, detail="New technician at maximum workload capacity")
        
    job.assigned_technician_id = new_tech.technician_id
    old_tech.current_jobs = 0
    new_tech.current_jobs = 1
    job.status = "ASSIGNED"
    
    audit = AuditEvent(tech_id=req.new_tech_id, tenant_id=x_tenant_id, event_type="JOB_REASSIGNED", new_status="ASSIGNED", reason=req.reason)
    db.add(audit)
    db.commit()
    
    redis_client.set(f"job:timer:{job_id}", "1")
    
    return {
        "status": "ASSIGNED",
        "previous_technician": {"tech_id": tech_id},
        "new_technician": {"tech_id": req.new_tech_id}
    }

@router.post("/{job_id}/assign")
def assign_job(
    job_id: int,
    req: JobAssignRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_permissions: str = Header(None, alias="X-Permissions"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    from app.models import OverrideAuditEvent
    with with_job_lock(str(job_id)):
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        tech = db.query(Technician).filter(Technician.tech_id == req.tech_id).first()
        if not tech:
            raise HTTPException(status_code=404, detail="Technician not found")
            
        job.assigned_technician_id = tech.technician_id
        job.status = "ASSIGNED"
        
        audit = OverrideAuditEvent(
            id=str(uuid.uuid4()),
            actor_id="admin",
            actor_role="admin",
            tenant_id=x_tenant_id,
            job_id=job.id,
            action="force_assign",
            before_state={},
            after_state={},
            justification=req.justification,
            reason="force_assign bypassing PlanningAgent"
        )
        db.add(audit)
        db.commit()
        
        return {
            "status": "ASSIGNED",
            "override": {
                "cooldown_bypassed": True,
                "exclusion_bypassed": True
            }
        }
