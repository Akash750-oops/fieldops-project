from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid
import json

from ..database import get_db
from ..models import Technician
from ..redis_client import get_redis_client
from ..logger import logger

router = APIRouter(
    prefix="/technicians",
    tags=["Dispatch"]
)

def verify_jwt_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    # Normally we would decode and validate the JWT here
    return authorization

@router.post("/{id}/heartbeat")
def technician_heartbeat(
    id: str,
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    log_extra = {"correlation_id": correlation_id, "tenant_id": x_tenant_id, "tech_id": id}

    # Validate UUID format
    try:
        uuid_obj = uuid.UUID(id, version=4)
    except ValueError:
        logger.warning("Invalid UUID format for tech_id", extra=log_extra)
        raise HTTPException(status_code=400, detail="Invalid technician ID format (must be UUID)")

    # Rate limiting: max 1 per 30 seconds
    rate_limit_key = f"rate_limit:{x_tenant_id}:{id}"
    if redis_client.get(rate_limit_key):
        logger.warning("Rate limit exceeded for heartbeat", extra=log_extra)
        raise HTTPException(status_code=429, detail="Too Many Requests")
    
    # Verify tenant isolation and existence
    tech = db.query(Technician).filter(Technician.tech_id == id).first()
    
    if not tech:
        logger.error("Technician not found", extra=log_extra)
        raise HTTPException(status_code=404, detail="Technician not found")
        
    if tech.tenant_id != x_tenant_id:
        logger.error("Cross-tenant access attempted", extra=log_extra)
        raise HTTPException(status_code=403, detail="Access denied")

    # Update database
    now = datetime.now(timezone.utc)
    tech.last_ping = now
    db.commit()

    # Update Redis cache with 60s TTL
    heartbeat_key = f"tech:heartbeat:{x_tenant_id}:{id}"
    redis_client.setex(heartbeat_key, 60, "AVAILABLE")
    
    # Set rate limit key
    redis_client.setex(rate_limit_key, 30, "1")

    logger.info("Heartbeat processed successfully", extra=log_extra)

    return {
        "tech_id": id,
        "last_ping": now.isoformat(),
        "status": "AVAILABLE"
    }
