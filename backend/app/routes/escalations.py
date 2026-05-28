from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging

from app.database import get_db
from app.models import Job, SLAEscalation, AuditEvent, Technician
from app.routes.dispatch import verify_jwt_token

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/escalations",
    tags=["Escalations"]
)

class ExtendSLARequest(BaseModel):
    minutes: int

class CancelJobRequest(BaseModel):
    reason: str

class ForceAssignRequest(BaseModel):
    tech_id: str
    reason: str

def get_active_escalation(db: Session, job_id: int):
    esc = db.query(SLAEscalation).filter(
        SLAEscalation.job_id == job_id,
        SLAEscalation.manager_responded_at.is_(None)
    ).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Active escalation not found for this job")
    return esc

def mark_responded(db: Session, esc: SLAEscalation, action: str):
    esc.manager_responded_at = datetime.now(timezone.utc)
    esc.action_taken = action
    db.commit()

@router.post("/{job_id}/extend-sla")
def extend_sla(
    job_id: int, 
    payload: ExtendSLARequest,
    db: Session = Depends(get_db),
    authorization: str = Depends(verify_jwt_token)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    esc = get_active_escalation(db, job_id)
    
    if job.sla_deadline:
        if job.sla_deadline.tzinfo is None:
            sla_dt = job.sla_deadline.replace(tzinfo=timezone.utc)
        else:
            sla_dt = job.sla_deadline
        job.sla_deadline = sla_dt + timedelta(minutes=payload.minutes)
    
    # Revert status to QUEUED so it can be re-dispatched normally
    old_status = job.status
    job.status = "QUEUED"
    
    audit = AuditEvent(
        tech_id="manager",
        tenant_id="system",
        event_type="ESCALATION_ACTION",
        old_status=old_status,
        new_status="QUEUED",
        reason=f"Manager extended SLA by {payload.minutes} minutes"
    )
    db.add(audit)
    
    mark_responded(db, esc, f"Extended SLA by {payload.minutes} min")
    
    logger.info(f"Escalation resolved: SLA extended for job {job_id}")
    return {"message": "SLA extended", "new_deadline": job.sla_deadline}

@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: int, 
    payload: CancelJobRequest,
    db: Session = Depends(get_db),
    authorization: str = Depends(verify_jwt_token)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    esc = get_active_escalation(db, job_id)
    
    old_status = job.status
    job.status = "CANCELLED"
    
    audit = AuditEvent(
        tech_id="manager",
        tenant_id="system",
        event_type="ESCALATION_ACTION",
        old_status=old_status,
        new_status="CANCELLED",
        reason=f"Manager cancelled job: {payload.reason}"
    )
    db.add(audit)
    
    mark_responded(db, esc, "Cancelled Job")
    
    logger.info(f"Escalation resolved: Job {job_id} cancelled")
    return {"message": "Job cancelled successfully"}

@router.post("/{job_id}/force-assign")
def force_assign(
    job_id: int, 
    payload: ForceAssignRequest,
    db: Session = Depends(get_db),
    authorization: str = Depends(verify_jwt_token)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    tech = db.query(Technician).filter(Technician.tech_id == payload.tech_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
        
    esc = get_active_escalation(db, job_id)
    
    old_status = job.status
    job.status = "ASSIGNED"
    job.assigned_technician_id = tech.technician_id
    
    audit = AuditEvent(
        tech_id=payload.tech_id,
        tenant_id="system",
        event_type="ESCALATION_ACTION",
        old_status=old_status,
        new_status="ASSIGNED",
        reason=f"Manager force-assigned tech: {payload.reason}"
    )
    db.add(audit)
    
    mark_responded(db, esc, f"Force Assigned to {payload.tech_id}")
    
    logger.info(f"Escalation resolved: Job {job_id} force-assigned to tech {payload.tech_id}")
    return {"message": "Job force-assigned successfully"}
