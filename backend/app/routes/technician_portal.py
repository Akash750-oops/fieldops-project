"""
Technician Portal API routes.

All endpoints are scoped to the authenticated technician.
Technicians can only access their own profile, their own assigned jobs,
and their own notifications.
"""

import uuid
import logging
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from ..database import get_db
from ..auth.dependencies import get_current_user, AuthenticatedUser, require_role
from ..auth.rbac import UserRole
from ..auth.password import hash_password, verify_password
from ..models import (
    Job, Technician, InAppNotification,
    TechnicianProfile, ServiceRequest,
)
from ..models.user import User
from ..portal_schemas import (
    TechnicianProfileCreate, TechnicianProfileUpdate, TechnicianProfileResponse,
    TechnicianJobResponse, TechnicianJobRejectRequest, TechnicianJobCompleteRequest,
    TechnicianJobActionRequest, TechnicianDashboardResponse, ChangePasswordRequest,
)
from ..services.enterprise_audit import audit_log, AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/technician",
    tags=["Technician Portal"],
)


def _get_tech_for_user(db: Session, user_id: str, tenant_id: str) -> Technician:
    """Find the Technician record linked to this user via tech_id, technician_id, name, or phone."""
    query = db.query(Technician)
    
    # 1. Direct match by tech_id or integer technician_id
    tech = query.filter(
        (Technician.tech_id == str(user_id)) |
        (Technician.technician_id == (int(user_id) if str(user_id).isdigit() else -1))
    ).first()
    
    if tech:
        return tech

    # 2. Match by TechnicianProfile or User linked to user_id
    profile = db.query(TechnicianProfile).filter(TechnicianProfile.user_id == str(user_id)).first()
    user = db.query(User).filter(User.id == str(user_id)).first()

    target_name = profile.full_name if (profile and profile.full_name) else (user.full_name if user else None)
    target_phone = profile.mobile_number if (profile and profile.mobile_number) else (user.phone_number if user else None)

    if target_name:
        tech_by_name = query.filter(func.lower(Technician.technician_name) == target_name.lower().strip()).first()
        if tech_by_name:
            tech_by_name.tech_id = str(user_id)
            try:
                db.commit()
            except Exception:
                db.rollback()
            return tech_by_name

    if target_phone:
        tech_by_phone = query.filter(Technician.phone_number == target_phone.strip()).first()
        if tech_by_phone:
            tech_by_phone.tech_id = str(user_id)
            try:
                db.commit()
            except Exception:
                db.rollback()
            return tech_by_phone

    return None


# ──────────────────────────────────────────────────
# Profile Endpoints
# ──────────────────────────────────────────────────

@router.get("/profile", response_model=TechnicianProfileResponse)
async def get_technician_profile(
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Get the current technician's profile."""
    profile = db.query(TechnicianProfile).filter(
        TechnicianProfile.user_id == current_user.user_id,
        TechnicianProfile.tenant_id == current_user.tenant_id,
    ).first()

    user = db.query(User).filter(User.id == current_user.user_id).first()

    if not profile:
        # Return a minimal response indicating profile not completed
        return TechnicianProfileResponse(
            id="",
            user_id=current_user.user_id,
            tenant_id=current_user.tenant_id,
            full_name=user.full_name if user else "",
            mobile_number=user.phone_number or "",
            profile_completed=False,
            email=user.email if user else "",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    # Calculate age
    age = None
    if profile.date_of_birth:
        today = date.today()
        age = today.year - profile.date_of_birth.year - (
            (today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day)
        )

    return TechnicianProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        tenant_id=profile.tenant_id,
        full_name=profile.full_name,
        profile_photo=profile.profile_photo,
        mobile_number=profile.mobile_number,
        date_of_birth=profile.date_of_birth,
        age=age,
        gender=profile.gender,
        address=profile.address,
        city=profile.city,
        state=profile.state,
        pincode=profile.pincode,
        emergency_contact=profile.emergency_contact,
        skills=profile.skills,
        experience=profile.experience,
        certifications=profile.certifications,
        profile_completed=profile.profile_completed,
        email=user.email if user else None,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.post("/profile", response_model=TechnicianProfileResponse, status_code=201)
async def create_technician_profile(
    data: TechnicianProfileCreate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Create technician profile (first-time setup)."""
    existing = db.query(TechnicianProfile).filter(
        TechnicianProfile.user_id == current_user.user_id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists. Use PUT to update.",
        )

    profile = TechnicianProfile(
        id=str(uuid.uuid4()),
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        full_name=data.full_name,
        profile_photo=data.profile_photo,
        mobile_number=data.mobile_number,
        date_of_birth=data.date_of_birth,
        gender=data.gender,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        emergency_contact=data.emergency_contact,
        skills=data.skills,
        experience=data.experience,
        certifications=data.certifications,
        profile_completed=True,
    )

    db.add(profile)

    # Sync to main technicians table for main app visibility
    try:
        skill_str = ", ".join(profile.skills) if profile.skills else "General Technician"
        loc_str = profile.address or f"{profile.city or ''}, {profile.state or ''}".strip(", ") or "Main Zone"
        tech = db.query(Technician).filter(
            (Technician.tech_id == str(current_user.user_id)) | 
            ((Technician.tenant_id == current_user.tenant_id) & (Technician.technician_name == profile.full_name))
        ).first()

        if not tech:
            tech = Technician(
                tech_id=str(current_user.user_id),
                tenant_id=current_user.tenant_id,
                technician_name=profile.full_name,
                technician_skill=skill_str,
                technician_location=loc_str,
                phone_number=profile.mobile_number,
                technician_status="AVAILABLE",
                current_jobs=0,
                max_jobs=5,
            )
            db.add(tech)
        else:
            tech.technician_name = profile.full_name
            if profile.mobile_number:
                tech.phone_number = profile.mobile_number
            tech.technician_skill = skill_str
            tech.technician_location = loc_str
    except Exception as sync_err:
        logger.warning(f"Could not auto-sync technician record: {sync_err}")

    audit_log(
        db,
        action=AuditAction.PROFILE_CREATED,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        role=current_user.role.value,
        entity_type="technician_profile",
        entity_id=profile.id,
        new_value={"full_name": data.full_name},
        request=request,
    )

    db.commit()
    db.refresh(profile)

    user = db.query(User).filter(User.id == current_user.user_id).first()

    age = None
    if profile.date_of_birth:
        today = date.today()
        age = today.year - profile.date_of_birth.year - (
            (today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day)
        )

    return TechnicianProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        tenant_id=profile.tenant_id,
        full_name=profile.full_name,
        profile_photo=profile.profile_photo,
        mobile_number=profile.mobile_number,
        date_of_birth=profile.date_of_birth,
        age=age,
        gender=profile.gender,
        address=profile.address,
        city=profile.city,
        state=profile.state,
        pincode=profile.pincode,
        emergency_contact=profile.emergency_contact,
        skills=profile.skills,
        experience=profile.experience,
        certifications=profile.certifications,
        profile_completed=profile.profile_completed,
        email=user.email if user else None,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.put("/profile", response_model=TechnicianProfileResponse)
async def update_technician_profile(
    data: TechnicianProfileUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Update technician profile."""
    profile = db.query(TechnicianProfile).filter(
        TechnicianProfile.user_id == current_user.user_id,
        TechnicianProfile.tenant_id == current_user.tenant_id,
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create it first.")

    update_data = data.model_dump(exclude_unset=True)
    old_values = {}
    for key, value in update_data.items():
        if value is not None:
            old_values[key] = getattr(profile, key, None)
            setattr(profile, key, value)

    profile.profile_completed = True

    # Sync to main technicians table for main app visibility
    try:
        skill_str = ", ".join(profile.skills) if profile.skills else "General Technician"
        loc_str = profile.address or f"{profile.city or ''}, {profile.state or ''}".strip(", ") or "Main Zone"
        tech = db.query(Technician).filter(
            (Technician.tech_id == str(current_user.user_id)) | 
            ((Technician.tenant_id == current_user.tenant_id) & (Technician.technician_name == profile.full_name))
        ).first()

        if not tech:
            tech = Technician(
                tech_id=str(current_user.user_id),
                tenant_id=current_user.tenant_id,
                technician_name=profile.full_name,
                technician_skill=skill_str,
                technician_location=loc_str,
                phone_number=profile.mobile_number,
                technician_status="AVAILABLE",
                current_jobs=0,
                max_jobs=5,
            )
            db.add(tech)
        else:
            tech.technician_name = profile.full_name
            if profile.mobile_number:
                tech.phone_number = profile.mobile_number
            tech.technician_skill = skill_str
            tech.technician_location = loc_str
    except Exception as sync_err:
        logger.warning(f"Could not auto-sync technician record on update: {sync_err}")

    audit_log(
        db,
        action=AuditAction.PROFILE_UPDATED,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        role=current_user.role.value,
        entity_type="technician_profile",
        entity_id=profile.id,
        old_value=old_values,
        new_value=update_data,
        request=request,
    )

    db.commit()
    db.refresh(profile)

    user = db.query(User).filter(User.id == current_user.user_id).first()
    age = None
    if profile.date_of_birth:
        today = date.today()
        age = today.year - profile.date_of_birth.year - (
            (today.month, today.day) < (profile.date_of_birth.month, profile.date_of_birth.day)
        )

    return TechnicianProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        tenant_id=profile.tenant_id,
        full_name=profile.full_name,
        profile_photo=profile.profile_photo,
        mobile_number=profile.mobile_number,
        date_of_birth=profile.date_of_birth,
        age=age,
        gender=profile.gender,
        address=profile.address,
        city=profile.city,
        state=profile.state,
        pincode=profile.pincode,
        emergency_contact=profile.emergency_contact,
        skills=profile.skills,
        experience=profile.experience,
        certifications=profile.certifications,
        profile_completed=profile.profile_completed,
        email=user.email if user else None,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# ──────────────────────────────────────────────────
# Change Password
# ──────────────────────────────────────────────────

@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Change technician password."""
    user = db.query(User).filter(User.id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.password_hash = hash_password(data.new_password)

    audit_log(
        db,
        action=AuditAction.PASSWORD_CHANGED,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        role=current_user.role.value,
        entity_type="user",
        entity_id=current_user.user_id,
        request=request,
    )

    db.commit()
    return {"message": "Password changed successfully"}


# ──────────────────────────────────────────────────
# Job Endpoints
# ──────────────────────────────────────────────────

def _get_assigned_jobs_query(db: Session, user_id: str, tenant_id: str):
    """Base query for jobs assigned to this technician."""
    tech = _get_tech_for_user(db, user_id, tenant_id)
    if not tech:
        return db.query(Job).filter(Job.id < 0)  # empty query
    return db.query(Job).filter(
        Job.assigned_technician_id == tech.technician_id
    )


@router.get("/jobs", response_model=list[TechnicianJobResponse])
async def get_assigned_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """List jobs assigned to the current technician."""
    query = _get_assigned_jobs_query(db, current_user.user_id, current_user.tenant_id)

    # Exclude rejected and completed for active view
    if status_filter:
        query = query.filter(func.lower(Job.status) == status_filter.lower())
    else:
        query = query.filter(
            ~func.lower(Job.status).in_(["rejected_by_technician", "completed", "closed", "cancelled"])
        )

    return query.order_by(Job.created_at.desc()).all()


@router.get("/jobs/history", response_model=list[TechnicianJobResponse])
async def get_job_history(
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """List completed/closed jobs for this technician."""
    query = _get_assigned_jobs_query(db, current_user.user_id, current_user.tenant_id)
    query = query.filter(
        func.lower(Job.status).in_(["completed", "closed"])
    )
    return query.order_by(Job.completed_at.desc()).all()


@router.get("/jobs/{job_id}", response_model=TechnicianJobResponse)
async def get_job_detail(
    job_id: int,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """View a specific job (only if assigned to this technician)."""
    tech = _get_tech_for_user(db, current_user.user_id, current_user.tenant_id)
    if not tech:
        raise HTTPException(status_code=403, detail="Technician record not found")

    job = db.query(Job).filter(
        Job.id == job_id,
        Job.assigned_technician_id == tech.technician_id,
        Job.tenant_id == current_user.tenant_id,
    ).first()

    if not job:
        raise HTTPException(status_code=403, detail="Job not found or not assigned to you")

    return job


@router.post("/jobs/{job_id}/accept")
async def accept_job(
    job_id: int,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Accept an assigned job."""
    tech = _get_tech_for_user(db, current_user.user_id, current_user.tenant_id)
    if not tech:
        raise HTTPException(status_code=403, detail="Technician record not found")

    job = db.query(Job).filter(
        Job.id == job_id,
        Job.assigned_technician_id == tech.technician_id,
        Job.tenant_id == current_user.tenant_id,
    ).first()

    if not job:
        raise HTTPException(status_code=403, detail="Job not found or not assigned to you")

    job.status = "ACCEPTED"

    audit_log(
        db,
        action=AuditAction.JOB_ACCEPTED,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        role=current_user.role.value,
        entity_type="job",
        entity_id=str(job_id),
        new_value={"status": "ACCEPTED"},
        request=request,
    )

    db.commit()
    return {"message": "Job accepted", "job_id": job_id, "status": "ACCEPTED"}


@router.post("/jobs/{job_id}/reject")
async def reject_job(
    job_id: int,
    data: TechnicianJobRejectRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """
    Reject an assigned job.

    - Saves rejection reason
    - Updates job status to REJECTED_BY_TECHNICIAN
    - Creates notification for dispatchers
    - Removes from technician's active list
    """
    tech = _get_tech_for_user(db, current_user.user_id, current_user.tenant_id)
    if not tech:
        raise HTTPException(status_code=403, detail="Technician record not found")

    job = db.query(Job).filter(
        Job.id == job_id,
        Job.assigned_technician_id == tech.technician_id,
        Job.tenant_id == current_user.tenant_id,
    ).first()

    if not job:
        raise HTTPException(status_code=403, detail="Job not found or not assigned to you")

    old_status = job.status
    job.status = "REJECTED_BY_TECHNICIAN"
    job.rejection_reason = data.reason
    job.rejected_at = datetime.now(timezone.utc)
    job.rejected_by_tech_id = tech.tech_id

    # Unassign the technician
    job.assigned_technician_id = None

    # Decrement tech's current jobs
    if tech.current_jobs and tech.current_jobs > 0:
        tech.current_jobs -= 1

    # Create in-app notification for dispatchers/admins
    notif = InAppNotification(
        id=str(uuid.uuid4()),
        tech_id=tech.tech_id or str(tech.technician_id),
        job_id=str(job_id),
        type="JOB_REJECTED",
        title="Job Rejected by Technician",
        body=f"{tech.technician_name} rejected Job #{job_id}: {data.reason}",
        status="UNREAD",
        priority="HIGH",
        tenant_id=current_user.tenant_id,
    )
    db.add(notif)

    audit_log(
        db,
        action=AuditAction.JOB_REJECTED_BY_TECHNICIAN,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        role=current_user.role.value,
        entity_type="job",
        entity_id=str(job_id),
        old_value={"status": old_status, "assigned_technician_id": tech.technician_id},
        new_value={"status": "REJECTED_BY_TECHNICIAN", "rejection_reason": data.reason},
        request=request,
    )

    db.commit()
    return {
        "message": "Job rejected",
        "job_id": job_id,
        "status": "REJECTED_BY_TECHNICIAN",
        "rejection_reason": data.reason,
    }


@router.post("/jobs/{job_id}/start")
async def start_job(
    job_id: int,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Start working on a job."""
    tech = _get_tech_for_user(db, current_user.user_id, current_user.tenant_id)
    if not tech:
        raise HTTPException(status_code=403, detail="Technician record not found")

    job = db.query(Job).filter(
        Job.id == job_id,
        Job.assigned_technician_id == tech.technician_id,
        Job.tenant_id == current_user.tenant_id,
    ).first()
    if not job:
        raise HTTPException(status_code=403, detail="Job not found or not assigned to you")

    old_status = job.status
    job.status = "IN_PROGRESS"
    job.on_site_at = datetime.now(timezone.utc)
    job.on_site_by = current_user.user_id

    audit_log(
        db, action=AuditAction.JOB_STARTED,
        tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        role=current_user.role.value, entity_type="job", entity_id=str(job_id),
        old_value={"status": old_status}, new_value={"status": "IN_PROGRESS"},
        request=request,
    )
    db.commit()
    return {"message": "Job started", "job_id": job_id, "status": "IN_PROGRESS"}


@router.post("/jobs/{job_id}/pause")
async def pause_job(
    job_id: int,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Pause a job in progress."""
    tech = _get_tech_for_user(db, current_user.user_id, current_user.tenant_id)
    if not tech:
        raise HTTPException(status_code=403, detail="Technician record not found")

    job = db.query(Job).filter(
        Job.id == job_id, Job.assigned_technician_id == tech.technician_id,
        Job.tenant_id == current_user.tenant_id,
    ).first()
    if not job:
        raise HTTPException(status_code=403, detail="Job not found or not assigned to you")

    old_status = job.status
    job.status = "PAUSED"

    audit_log(
        db, action=AuditAction.JOB_PAUSED,
        tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        role=current_user.role.value, entity_type="job", entity_id=str(job_id),
        old_value={"status": old_status}, new_value={"status": "PAUSED"},
        request=request,
    )
    db.commit()
    return {"message": "Job paused", "job_id": job_id, "status": "PAUSED"}


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: int,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Resume a paused job."""
    tech = _get_tech_for_user(db, current_user.user_id, current_user.tenant_id)
    if not tech:
        raise HTTPException(status_code=403, detail="Technician record not found")

    job = db.query(Job).filter(
        Job.id == job_id, Job.assigned_technician_id == tech.technician_id,
        Job.tenant_id == current_user.tenant_id,
    ).first()
    if not job:
        raise HTTPException(status_code=403, detail="Job not found or not assigned to you")

    old_status = job.status
    job.status = "IN_PROGRESS"

    audit_log(
        db, action=AuditAction.JOB_RESUMED,
        tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        role=current_user.role.value, entity_type="job", entity_id=str(job_id),
        old_value={"status": old_status}, new_value={"status": "IN_PROGRESS"},
        request=request,
    )
    db.commit()
    return {"message": "Job resumed", "job_id": job_id, "status": "IN_PROGRESS"}


@router.post("/jobs/{job_id}/complete")
async def complete_job(
    job_id: int,
    data: TechnicianJobCompleteRequest,
    request: Request,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Complete a job with notes, photos, and optional signature."""
    tech = _get_tech_for_user(db, current_user.user_id, current_user.tenant_id)
    if not tech:
        raise HTTPException(status_code=403, detail="Technician record not found")

    job = db.query(Job).filter(
        Job.id == job_id, Job.assigned_technician_id == tech.technician_id,
        Job.tenant_id == current_user.tenant_id,
    ).first()
    if not job:
        raise HTTPException(status_code=403, detail="Job not found or not assigned to you")

    old_status = job.status
    job.status = "COMPLETED"
    job.completed_at = datetime.now(timezone.utc)
    job.completed_by = current_user.user_id
    if data.completion_notes:
        job.work_report = data.completion_notes

    # Decrement tech's current jobs
    if tech.current_jobs and tech.current_jobs > 0:
        tech.current_jobs -= 1

    audit_log(
        db, action=AuditAction.JOB_COMPLETED,
        tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        role=current_user.role.value, entity_type="job", entity_id=str(job_id),
        old_value={"status": old_status},
        new_value={"status": "COMPLETED", "completion_notes": data.completion_notes},
        request=request,
    )
    db.commit()
    return {"message": "Job completed", "job_id": job_id, "status": "COMPLETED"}


# ──────────────────────────────────────────────────
# Notifications
# ──────────────────────────────────────────────────

@router.get("/notifications")
async def get_notifications(
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Get technician notifications, auto-syncing notifications from assigned jobs."""
    tech = _get_tech_for_user(db, current_user.user_id, current_user.tenant_id)

    search_ids = [str(current_user.user_id)]
    if tech:
        search_ids.append(str(tech.technician_id))
        if tech.tech_id:
            search_ids.append(str(tech.tech_id))

    notifications = db.query(InAppNotification).filter(
        InAppNotification.tech_id.in_(search_ids)
    ).order_by(InAppNotification.created_at.desc()).limit(100).all()

    # Sync notifications from active assigned jobs if notification entry is missing
    if tech:
        assigned_jobs = db.query(Job).filter(
            Job.assigned_technician_id == tech.technician_id,
            ~func.lower(Job.status).in_(["rejected_by_technician", "completed", "closed", "cancelled"])
        ).all()

        existing_job_ids = {str(n.job_id) for n in notifications if n.job_id}

        new_added = False
        for job in assigned_jobs:
            if str(job.id) not in existing_job_ids:
                new_notif = InAppNotification(
                    id=str(uuid.uuid4()),
                    tech_id=str(current_user.user_id),
                    job_id=str(job.id),
                    type="JOB_ASSIGNED",
                    title="New Job Assigned",
                    body=f"You have been assigned to Job #{job.id}: {job.service_type or 'Service Request'} at {job.location or 'Customer location'}.",
                    status="UNREAD",
                    priority=job.priority or "HIGH",
                    created_at=job.created_at or datetime.now(timezone.utc)
                )
                db.add(new_notif)
                new_added = True

        if new_added:
            try:
                db.commit()
                notifications = db.query(InAppNotification).filter(
                    InAppNotification.tech_id.in_(search_ids)
                ).order_by(InAppNotification.created_at.desc()).limit(100).all()
            except Exception:
                db.rollback()

    unread_count = sum(1 for n in notifications if n.status == "UNREAD")

    return {
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "message": n.body,
                "isRead": n.status != "UNREAD",
                "createdAt": n.created_at.isoformat() if n.created_at else None,
                "jobId": n.job_id,
            }
            for n in notifications
        ],
        "unread_count": unread_count,
    }


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    notif = db.query(InAppNotification).filter(
        InAppNotification.id == notification_id,
    ).first()
    if notif:
        notif.status = "READ"
        notif.read_at = datetime.now(timezone.utc)
        db.commit()
    return {"message": "Marked as read"}


@router.put("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read."""
    tech = _get_tech_for_user(db, current_user.user_id, current_user.tenant_id)
    tech_id = tech.tech_id if tech else current_user.user_id

    db.query(InAppNotification).filter(
        InAppNotification.tech_id == tech_id,
        InAppNotification.status == "UNREAD",
    ).update({"status": "READ", "read_at": datetime.now(timezone.utc)})
    db.commit()
    return {"message": "All notifications marked as read"}


# ──────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────

@router.get("/dashboard", response_model=TechnicianDashboardResponse)
async def get_technician_dashboard(
    current_user: AuthenticatedUser = Depends(require_role(UserRole.TECHNICIAN)),
    db: Session = Depends(get_db),
):
    """Get technician dashboard statistics."""
    tech = _get_tech_for_user(db, current_user.user_id, current_user.tenant_id)
    if not tech:
        return TechnicianDashboardResponse()

    base = db.query(Job).filter(
        Job.assigned_technician_id == tech.technician_id,
        Job.tenant_id == current_user.tenant_id,
    )

    today = datetime.now(timezone.utc).date()

    total_assigned = base.count()
    active = base.filter(
        ~func.lower(Job.status).in_(["completed", "closed", "cancelled", "rejected_by_technician"])
    ).count()
    completed_today = base.filter(
        Job.status == "COMPLETED",
        func.date(Job.completed_at) == today,
    ).count()
    pending = base.filter(
        func.lower(Job.status).in_(["assigned", "active"])
    ).count()
    total_completed = base.filter(
        func.lower(Job.status).in_(["completed", "closed"])
    ).count()

    return TechnicianDashboardResponse(
        total_assigned=total_assigned,
        active_jobs=active,
        completed_today=completed_today,
        pending_acceptance=pending,
        total_completed=total_completed,
    )
