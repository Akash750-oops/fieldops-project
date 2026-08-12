from fastapi import APIRouter, Depends, HTTPException, Header, status, Request, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
import uuid
import json

from ..database import get_db
from ..models import Technician, Job, AuditEvent, InAppNotification, AssignmentOverride
from ..redis_client import get_redis_client
from ..logger import logger
from ..schemas import HeartbeatPayload, AvailabilityResponse
from ..services.timer_service import TimerService
from ..services.cooldown_service import CooldownService
from ..services.socket_manager import sio, emit_notification

class OverrideRequest(BaseModel):
    technician_id: str
    justification: str
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None

router = APIRouter(
    prefix="/technicians",
    tags=["Dispatch"]
)

security = HTTPBearer()

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    # Normally we would decode and validate the JWT here: credentials.credentials
    return credentials.credentials

@router.post("/{id}/heartbeat")
def technician_heartbeat(
    id: str,
    request: Request,
    payload: HeartbeatPayload = Body(default_factory=HeartbeatPayload),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    log_extra = {"correlation_id": correlation_id, "tenant_id": x_tenant_id, "tech_id": id}

    try:
        # Validate UUID format
        try:
            uuid.UUID(id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format")

        # Rate limiting: max 1 per 30 seconds
        rate_limit_key = f"rate_limit:{x_tenant_id}:{id}"
        try:
            if not redis_client.set(rate_limit_key, "1", ex=30, nx=True):
                logger.warning("Rate limit exceeded for heartbeat", extra=log_extra)
                raise HTTPException(status_code=429, detail="Too Many Requests")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.warning(f"Redis error checking rate limit: {e}", extra=log_extra)
        
        # Verify tenant isolation and existence
        tech = db.query(Technician).filter(Technician.tech_id == id).first()
        
        if not tech:
            logger.error("Technician not found", extra=log_extra)
            raise HTTPException(status_code=404, detail="Technician not found")
            
        if tech.tenant_id and tech.tenant_id != x_tenant_id:
            logger.error("Cross-tenant access attempted", extra=log_extra)
            raise HTTPException(status_code=403, detail="Access denied")

        # Update database
        now = datetime.now(timezone.utc)
        tech.last_ping = now
        db.commit()

        # Build JSON payload for Redis cache
        cache_data = {
            "tech_id": id,
            "status": tech.technician_status,
            "last_ping": now.isoformat(),
            "active_jobs": tech.current_jobs,
            "last_lat": payload.last_lat,
            "last_lng": payload.last_lng
        }

        # Update Redis cache with 60s TTL
        heartbeat_key = f"tech:availability:{x_tenant_id}:{id}"
        try:
            redis_client.setex(heartbeat_key, 60, json.dumps(cache_data))
        except Exception as e:
            logger.warning(f"Redis error caching heartbeat: {e}", extra=log_extra)

        logger.info("Heartbeat processed and cached successfully", extra=log_extra)

        return cache_data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        import traceback
        return {"debug_crash": str(e), "traceback": traceback.format_exc()}

@router.get("/metrics")
def get_metrics(redis_client = Depends(get_redis_client)):
    now = datetime.now(timezone.utc)
    hour_str = now.strftime("%Y-%m-%d-%H")
    metric_key = f"metrics:offline_events:{hour_str}"
    
    val = redis_client.get(metric_key)
    offline_events = int(val) if val else 0
    
    return {
        "offline_events_current_hour": offline_events
    }

@router.get("/{id}/availability", response_model=AvailabilityResponse)
def get_technician_availability(
    id: str,
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    log_extra = {"correlation_id": correlation_id, "tenant_id": x_tenant_id, "tech_id": id}

    heartbeat_key = f"tech:availability:{x_tenant_id}:{id}"
    try:
        cached_data = redis_client.get(heartbeat_key)
    
        if cached_data:
            logger.info("Cache hit for availability", extra=log_extra)
            return json.loads(cached_data)
    except Exception as e:
        logger.warning(f"Redis error checking availability cache: {e}", extra=log_extra)

    logger.info("Cache miss for availability, falling back to database", extra=log_extra)
    
    # Fallback to database
    tech = db.query(Technician).filter(Technician.tech_id == id).first()
    
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
        
    if tech.tenant_id and tech.tenant_id != x_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Return constructed object
    return {
        "tech_id": id,
        "status": tech.technician_status,
        "last_ping": tech.last_ping.isoformat() if tech.last_ping else datetime.now(timezone.utc).isoformat(),
        "active_jobs": tech.current_jobs,
        "last_lat": None,
        "last_lng": None
    }

@router.post("/{id}/invalidate-cache")
def invalidate_technician_cache(
    id: str,
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    redis_client = Depends(get_redis_client)
):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    log_extra = {"correlation_id": correlation_id, "tenant_id": x_tenant_id, "tech_id": id}

    heartbeat_key = f"tech:availability:{x_tenant_id}:{id}"
    
    if redis_client.delete(heartbeat_key):
        logger.info("Cache invalidated successfully", extra=log_extra)
        return {"message": "Cache invalidated successfully"}
    else:
        logger.info("Cache invalidation attempted but key not found", extra=log_extra)
        return {"message": "Cache key not found"}

@router.post("/assignments/{job_id}/override")
async def admin_override_assignment(
    job_id: int,
    request: OverrideRequest,
    req: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    correlation_id = req.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    log_extra = {"correlation_id": correlation_id, "tenant_id": x_tenant_id, "job_id": job_id}
    
    # Role check (admin/dispatcher/manager only)
    auth_lower = authorization.lower()
    if "admin" not in auth_lower and "dispatcher" not in auth_lower and "manager" not in auth_lower:
        raise HTTPException(status_code=403, detail="Admin, Manager or Dispatcher role required for override")
        
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Support both tech_id (UUID string) and technician_id (integer)
    tech = db.query(Technician).filter(Technician.tech_id == request.technician_id).first()
    if not tech and request.technician_id.isdigit():
        tech = db.query(Technician).filter(Technician.technician_id == int(request.technician_id)).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
        
    # Track previous technician if assigned
    prev_id = None
    prev_name = "Unassigned"
    if job.assigned_technician_id:
        previous_tech = db.query(Technician).filter(Technician.technician_id == job.assigned_technician_id).first()
        if previous_tech:
            prev_id = previous_tech.technician_id
            prev_name = previous_tech.technician_name
            
    # Resolve actor details
    actor_role = request.actor_role or ("admin" if "admin" in auth_lower else "manager" if "manager" in auth_lower else "dispatcher")
    actor_name = request.actor_name or (
        "Admin Rajesh" if actor_role == "admin" else 
        "Manager Priya" if actor_role == "manager" else 
        "Dispatcher John"
    )
        
    audit = AuditEvent(
        tech_id=tech.tech_id or str(tech.technician_id),
        tenant_id=x_tenant_id,
        event_type="ADMIN_OVERRIDE",
        old_status=request.justification[:30],
        new_status="OVERRIDDEN"
    )
    db.add(audit)
    
    # Update job and increment workload
    job.assigned_technician_id = tech.technician_id
    job.status = "ASSIGNED"
    
    override_log = AssignmentOverride(
        job_id=job.id,
        actor_name=actor_name,
        actor_role=actor_role,
        justification=request.justification,
        previous_technician_id=prev_id,
        previous_technician_name=prev_name,
        new_technician_id=tech.technician_id,
        new_technician_name=tech.technician_name
    )
    db.add(override_log)

    notif_id = str(uuid.uuid4())
    if tech.tech_id:
        db_notif = InAppNotification(
            id=notif_id,
            tech_id=tech.tech_id,
            job_id=str(job.id),
            type="JOB_ASSIGNED",
            title="Forced Job Assignment",
            body=f"You have been manually force-assigned to job: {job.service_type} at {job.location}. Reason: {request.justification}",
            status="UNREAD",
            priority="HIGH",
            created_at=datetime.now(timezone.utc)
        )
        db.add(db_notif)

    db.commit()
    db.refresh(override_log)
    
    # Construct override log dict for WebSocket broadcast
    override_data = {
        "id": override_log.id,
        "job_id": override_log.job_id,
        "actor_name": override_log.actor_name,
        "actor_role": override_log.actor_role,
        "justification": override_log.justification,
        "previous_technician_id": override_log.previous_technician_id,
        "previous_technician_name": override_log.previous_technician_name,
        "new_technician_id": override_log.new_technician_id,
        "new_technician_name": override_log.new_technician_name,
        "created_at": override_log.created_at.isoformat() if override_log.created_at else datetime.now(timezone.utc).isoformat()
    }
    
    # Broadcast new override to WebSocket clients
    await sio.emit("override:new", override_data)
    
    # Notify technician in real-time
    if tech.tech_id:
        payload = {
            "id": notif_id,
            "tech_id": tech.tech_id,
            "job_id": str(job.id),
            "type": "JOB_ASSIGNED",
            "title": "Forced Job Assignment",
            "body": f"You have been manually force-assigned to job: {job.service_type} at {job.location}. Reason: {request.justification}",
            "status": "UNREAD",
            "priority": "HIGH",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "job": {
                "id": job.id,
                "title": f"{job.service_type} - {job.location}",
                "description": job.issue_description,
                "location": job.location,
                "priority": job.priority,
                "status": job.status
            }
        }
        await emit_notification(tech.tech_id, payload)
        
    # Dismiss alert banner for all dispatchers
    await sio.emit("redispatch:dismiss", {
        "job_id": job.id
    })
    
    redis_client = get_redis_client()
    TimerService.start_timer(redis_client, str(job.id), str(tech.tech_id))
    CooldownService.clear_cooldown(redis_client, str(job.id), str(tech.tech_id))
    
    logger.info("Admin override applied", extra=log_extra)
    return {"message": "Override applied successfully", "job_id": job_id, "technician_id": request.technician_id}
