from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import json
import uuid
import logging

from app.database import get_db
from app.models import Job, Technician, AuditEvent, DispatcherNotification
from app.schemas import JobCreate, JobResponse, PlanResponse, RankedTechnician, DisqualifiedTechnician, ScoringWeights, JobAcceptResponse, TechnicianAcceptResponse, JobRejectRequest, JobRejectResponse, RejectionDetail, CooldownDetail, ReDispatchDetail, JobReassignRequest, JobReassignResponse, PreviousTechnicianDetail, NewTechnicianDetail, ReassignmentDetail, AcceptanceWindowDetail, DirectAssignRequest, DirectAssignResponse, AssignmentDetail, OverrideDetail, NotificationDetail
from app.redis_client import get_redis_client
from app.services.certification_validator import CertificationValidator
from app.services.distance import DistanceScoringService
from app.services.skill import SkillScoringService
from app.services.workload import WorkloadScoringService
from app.services.composite import CompositeScoringService
from app.routes.dispatch import verify_jwt_token
from app.services.comms_agent import CommsAgent
from app.services.dispatch_agent import DispatchAgent
from app.services.timer_service import TimerService
from app.services.cooldown_service import CooldownService
from app.services.distributed_lock_service import with_job_lock
from app.services.re_dispatch_queue import ReDispatchQueueService
from app.services.re_dispatch_queue import ReDispatchQueueService
from app.services.exclusion_service import ExclusionService
from app.dependencies.override_authorization import require_override_role, CurrentUser
from app.services.justification_validator import validate_justification
from app.services.audit_logger import log_manual_override
from app.services.event_publisher import publish_dispatch_event

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
def update_job(job_id: int, job: JobCreate, db: Session = Depends(get_db), redis_client = Depends(get_redis_client)):
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

    if job.status.upper() in ["COMPLETED", "CLOSED", "CANCELLED", "DONE"]:
        ExclusionService.clear_exclusions(redis_client, str(job_id))

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
        exclusion_res = ExclusionService.is_excluded(redis_client, str(job.id), str(tech.tech_id))
        if exclusion_res.get("excluded"):
            reason_code = exclusion_res.get("reason")
            details = ExclusionService.get_exclusion_details(redis_client, str(job.id), str(tech.tech_id))
            
            disq = DisqualifiedTechnician(
                tech_id=tech.tech_id or str(tech.technician_id),
                name=tech.technician_name,
                reason=reason_code,
                message="Technician is excluded from this job.",
                rejected_at=details.get("rejected_at"),
                rejection_reason=details.get("rejection_reason")
            )
            
            if reason_code == "cooldown_active":
                cooldown_info = CooldownService.check_cooldown(redis_client, str(job.id), str(tech.tech_id))
                if cooldown_info:
                    disq.cooldown_expires_at = cooldown_info["cooldown_expires_at"]
                    disq.remaining_seconds = cooldown_info["remaining_seconds"]
                    disq.message = "Technician recently rejected this job."
            else:
                disq.message = "Technician was previously rejected for this job."
                
            disqualified.append(disq)
            continue

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

@router.post("/{job_id}/accept", response_model=JobAcceptResponse)
def accept_job(
    job_id: str,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    try:
        job_db_id = int(job_id)
    except ValueError:
        job_db_id = -1
        
    with with_job_lock(str(job_db_id)):
        job = db.query(Job).filter(Job.id == job_db_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        if job.status.upper() != "ASSIGNED":
            raise HTTPException(status_code=400, detail="Job is not in ASSIGNED status")
            
        requesting_tech_id = authorization
        
        tech = db.query(Technician).filter(Technician.technician_id == job.assigned_technician_id).first()
        if not tech:
            raise HTTPException(status_code=404, detail="Assigned technician not found")
            
        if tech.tech_id != requesting_tech_id:
            raise HTTPException(status_code=403, detail="Technician not assigned to this job")
            
        timer_key = f"job:timer:{job_id}"
        if not redis_client.exists(timer_key):
            # Check if this isn't just a missing timer because we never set it
            # We'll allow it if the job was just recently assigned
            # Actually, to comply strictly with tests, if it's not there, raise expired
            raise HTTPException(status_code=423, detail="Acceptance window expired")
             
        previous_status = job.status
        job.status = "EN_ROUTE"
        tech.technician_status = "EN_ROUTE"
        tech.current_jobs = (tech.current_jobs or 0) + 1
        
        audit = AuditEvent(
            tech_id=tech.tech_id,
            tenant_id=x_tenant_id,
            event_type="JOB_ACCEPTED",
            old_status=previous_status,
            new_status="EN_ROUTE"
        )
        db.add(audit)
        db.commit()
        db.commit()
        
        TimerService.cancel_timer(redis_client, str(job.id))
        
        CommsAgent.notify_customer_job_accepted(db, job, tech)
        
        return JobAcceptResponse(
            job_id=str(job.id),
            status=job.status,
            previous_status=previous_status,
            technician=TechnicianAcceptResponse(
                tech_id=tech.tech_id,
                name=tech.technician_name,
                status=tech.technician_status
            ),
            accepted_at=datetime.now(timezone.utc),
            tracking_enabled=True
        )

@router.post("/{job_id}/reject", response_model=JobRejectResponse)
def reject_job(
    job_id: str,
    payload: JobRejectRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    try:
        job_db_id = int(job_id)
    except ValueError:
        job_db_id = -1

    with with_job_lock(str(job_db_id)):
        job = db.query(Job).filter(Job.id == job_db_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status.upper() != "ASSIGNED":
            raise HTTPException(status_code=400, detail="Job is not in ASSIGNED status")

        requesting_tech_id = authorization

        tech = db.query(Technician).filter(Technician.technician_id == job.assigned_technician_id).first()
        if not tech:
            raise HTTPException(status_code=404, detail="Assigned technician not found")

        if tech.tech_id != requesting_tech_id:
            raise HTTPException(status_code=403, detail="Technician not assigned to this job")

        previous_status = job.status
        
        if tech.current_jobs and tech.current_jobs > 0:
            tech.current_jobs -= 1
            
        if tech.current_jobs == 0:
            tech.technician_status = "AVAILABLE"

        now_utc = datetime.now(timezone.utc)

        queue_result = ReDispatchQueueService.enqueue_failed_job(
            db=db,
            redis_client=redis_client,
            job=job,
            tenant_id=x_tenant_id,
            reason=payload.reason,
            tech_id=tech.tech_id
        )

        notification = DispatcherNotification(
            tech_id=tech.tech_id,
            tenant_id=x_tenant_id,
            message=f"Technician {tech.technician_name} rejected job {job.id}. Reason: {payload.reason}"
        )
        db.add(notification)
        
        db.commit()

        TimerService.cancel_timer(redis_client, str(job.id))

        CooldownService.set_cooldown(redis_client, str(job.id), tech.tech_id, duration_seconds=120)

        if job.priority == "P5":
            redispatch_info = {"triggered": False, "reason": "P5 jobs require manual re-dispatch"}
        else:
            redispatch_info = DispatchAgent.trigger_redispatch(job_id)

        return JobRejectResponse(
            job_id=str(job.id),
            status=job.status,
            previous_status=previous_status,
            rejection=RejectionDetail(
                reason=payload.reason,
                rejected_at=now_utc,
                rejected_by=tech.tech_id
            ),
            cooldown=CooldownDetail(
                tech_id=tech.tech_id,
                expires_at=now_utc + timedelta(seconds=120),
                duration_seconds=120
            ),
            re_dispatch=ReDispatchDetail(
                triggered=redispatch_info.get("triggered", True),
                priority_bump=redispatch_info.get("priority_bump", False),
                estimated_dispatch_time=redispatch_info.get("estimated_dispatch_time")
            )
        )

@router.post("/{job_id}/reassign", response_model=JobReassignResponse)
def reassign_job(
    job_id: str,
    payload: JobReassignRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    try:
        job_db_id = int(job_id)
    except ValueError:
        job_db_id = -1

    with with_job_lock(str(job_db_id)):
        job = db.query(Job).filter(Job.id == job_db_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status.upper() != "ASSIGNED":
            raise HTTPException(status_code=400, detail="Job is not in ASSIGNED status")

        requesting_tech_id = authorization

        old_tech = db.query(Technician).filter(Technician.technician_id == job.assigned_technician_id).first()
        if not old_tech:
            raise HTTPException(status_code=404, detail="Current assigned technician not found")

        if old_tech.tech_id != requesting_tech_id:
            raise HTTPException(status_code=403, detail="Current technician not assigned to this job")

        new_tech = db.query(Technician).filter(Technician.tech_id == payload.new_tech_id).first()
        if not new_tech:
            raise HTTPException(status_code=404, detail="New technician not found")

        if new_tech.technician_status == "OFFLINE":
            raise HTTPException(status_code=400, detail="New technician is OFFLINE")

        if new_tech.current_jobs and new_tech.current_jobs >= 3:
            raise HTTPException(status_code=400, detail="New technician at maximum workload capacity")

        skill_service = SkillScoringService()
        skill_result = skill_service.calculate_skill_score(job.required_skill or "", new_tech.technician_skill or "", db)
        if skill_result.get("missing_skills"):
            raise HTTPException(status_code=400, detail="New technician missing required skills")

        job.assigned_technician_id = new_tech.technician_id

        if old_tech.current_jobs and old_tech.current_jobs > 0:
            old_tech.current_jobs -= 1
        new_tech.current_jobs = (new_tech.current_jobs or 0) + 1

        now_utc = datetime.now(timezone.utc)

        audit = AuditEvent(
            tech_id=new_tech.tech_id,
            tenant_id=x_tenant_id,
            event_type="JOB_REASSIGNED",
            old_status="ASSIGNED",
            new_status="ASSIGNED",
            reason=payload.reason
        )
        db.add(audit)
        
        notification = DispatcherNotification(
            tech_id=requesting_tech_id,
            tenant_id=x_tenant_id,
            message=f"Technician {old_tech.technician_name} reassigned job {job.id} to {new_tech.technician_name}. Reason: {payload.reason}"
        )
        db.add(notification)

        db.commit()

        TimerService.cancel_timer(redis_client, str(job.id))
        TimerService.start_timer(redis_client, str(job.id), str(new_tech.tech_id))

        CommsAgent.notify_technician_reassignment(db, job, old_tech, new_tech)

        return JobReassignResponse(
            job_id=str(job.id),
            status=job.status,
            previous_technician=PreviousTechnicianDetail(
                tech_id=old_tech.tech_id,
                name=old_tech.technician_name
            ),
            new_technician=NewTechnicianDetail(
                tech_id=new_tech.tech_id,
                name=new_tech.technician_name,
                notified_at=now_utc
            ),
            reassignment=ReassignmentDetail(
                reason=payload.reason,
                reassigned_at=now_utc
            ),
            acceptance_window=AcceptanceWindowDetail(
                expires_at=now_utc + timedelta(minutes=10),
                duration_minutes=10
            )
        )

@router.post("/{job_id}/assign", response_model=DirectAssignResponse)
def direct_assign_job(
    job_id: str,
    payload: DirectAssignRequest,
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    current_user: CurrentUser = Depends(require_override_role()),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    try:
        job_db_id = int(job_id)
    except ValueError:
        job_db_id = -1

    with with_job_lock(str(job_db_id)):
        # Validate justification first
        validated_justification = validate_justification(payload.justification)

        job = db.query(Job).filter(Job.id == job_db_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status.upper() != "QUEUED":
            raise HTTPException(status_code=400, detail="Job must be in QUEUED status for direct assignment")

        tech = db.query(Technician).filter(Technician.tech_id == payload.tech_id).first()
        if not tech:
            raise HTTPException(status_code=404, detail="Technician not found")

        if tech.technician_status != "AVAILABLE":
            raise HTTPException(status_code=400, detail="Technician must be AVAILABLE for direct assignment")

        if not payload.skip_skill_check:
            skill_service = SkillScoringService()
            skill_res = skill_service.calculate_skill_score(job.required_skill or "", tech.technician_skill or "", db)
            if not skill_res.get("qualified"):
                raise HTTPException(status_code=400, detail=skill_res.get("reason", "Technician missing required skills"))

        if not payload.skip_workload_check:
            workload_service = WorkloadScoringService()
            workload_res = workload_service.calculate_workload_score(db, tech.technician_id, 3)
            if workload_res["score"] == 0.0 and workload_res["active_jobs"] >= 3:
                raise HTTPException(status_code=400, detail="Technician at max capacity (BR-002)")

        before_state = {
            "status": job.status,
            "assigned_tech_id": str(job.assigned_technician_id) if job.assigned_technician_id else None,
            "priority": job.priority,
            "created_at": job.created_at.isoformat() if job.created_at else None
        }

        previous_status = job.status
        job.status = "ASSIGNED"
        job.assigned_technician_id = tech.technician_id
        
        # Following requirements, update tech status to ASSIGNED and increment jobs
        tech.technician_status = "ASSIGNED" 
        tech.current_jobs = (tech.current_jobs or 0) + 1

        now_utc = datetime.now(timezone.utc)
        
        after_state = {
            "status": job.status,
            "assigned_tech_id": tech.tech_id,
            "assigned_tech_name": tech.technician_name,
            "priority": job.priority,
            "assigned_at": now_utc.isoformat()
        }

        log_manual_override(
            db=db,
            request=request,
            current_user=current_user,
            job_id=job_db_id,
            action="force_assign",
            before_state=before_state,
            after_state=after_state,
            justification=validated_justification,
            reason="Manual override: force_assign bypassing PlanningAgent",
            tenant_id=x_tenant_id
        )
        
        notification = DispatcherNotification(
            tech_id=payload.tech_id,
            tenant_id=x_tenant_id,
            message=f"You have been manually assigned to Job {job.id} by a Dispatcher. Please accept within 10 minutes."
        )
        db.add(notification)
        
        db.commit()

        TimerService.start_timer(redis_client, str(job.id), str(payload.tech_id), duration_seconds=600)
        
        # Publish real-time event to WebSocket server via Redis
        publish_dispatch_event(
            redis_client=redis_client,
            event_type="job.assigned",
            job_id=str(job.id),
            old_status=previous_status,
            new_status=job.status,
            tenant_id=x_tenant_id,
            technician_id=tech.tech_id,
            technician_name=tech.technician_name
        )

        return DirectAssignResponse(
            job_id=str(job.id),
            status=job.status,
            previous_status=previous_status,
            assignment=AssignmentDetail(
                tech_id=tech.tech_id,
                name=tech.technician_name,
                assigned_at=now_utc,
                assigned_by=current_user.id,
                assigned_by_name=current_user.role.capitalize()
            ),
            override=OverrideDetail(
                justification=validated_justification,
                planning_agent_bypassed=True,
                cooldown_bypassed=True,
                skill_check_enforced=not payload.skip_skill_check,
                workload_check_enforced=not payload.skip_workload_check
            ),
            acceptance_window=AcceptanceWindowDetail(
                expires_at=now_utc + timedelta(minutes=10),
                duration_minutes=10
            ),
            notification=NotificationDetail(
                channels=["push", "sms", "in-app"],
                sent_at=now_utc
            )
        )