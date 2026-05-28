from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models import OverrideAuditEvent, Job
from app.schemas import OverrideAuditResponse
from app.dependencies.override_authorization import verify_jwt_token

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/audit",
    tags=["Audit"]
)

@router.get("/overrides/{job_id}", response_model=list[OverrideAuditResponse])
def get_override_audits_for_job(
    job_id: str,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        job_db_id = int(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    # Optional: Verify job belongs to tenant
    job = db.query(Job).filter(Job.id == job_db_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    audits = db.query(OverrideAuditEvent).filter(
        OverrideAuditEvent.job_id == job_db_id,
        OverrideAuditEvent.tenant_id == x_tenant_id
    ).order_by(OverrideAuditEvent.created_at.desc()).all()

    return audits
