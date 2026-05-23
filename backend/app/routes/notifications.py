from fastapi import APIRouter, Depends, HTTPException, Header, Request, Form
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from .dispatch import verify_jwt_token
from ..database import get_db
from ..models import Technician, Job, SMSDelivery
from ..schemas import FCMTokenRegistration, NotificationSendRequest, NotificationSendResponse, SMSSendRequest
from ..logger import logger
from ..services.fcm import send_job_assignment_notification
from ..services.twilio_sms import send_job_assignment_sms

router = APIRouter(
    tags=["Notifications"]
)

@router.post("/technicians/{id}/fcm-token")
def register_fcm_token(
    id: str,
    payload: FCMTokenRegistration,
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    log_extra = {"correlation_id": correlation_id, "tenant_id": x_tenant_id, "tech_id": id}

    try:
        uuid_obj = uuid.UUID(id, version=4)
    except ValueError:
        logger.warning("Invalid technician ID format", extra=log_extra)
        raise HTTPException(status_code=400, detail="Invalid technician ID format (must be UUID)")

    tech = db.query(Technician).filter(Technician.tech_id == id).first()
    if not tech:
        logger.error("Technician not found", extra=log_extra)
        raise HTTPException(status_code=404, detail="Technician not found")
        
    if tech.tenant_id and tech.tenant_id != x_tenant_id:
        logger.error("Access denied for tenant", extra=log_extra)
        raise HTTPException(status_code=403, detail="Access denied")

    tech.fcm_token = payload.token
    tech.device_type = payload.device_type
    db.commit()
    
    logger.info(f"Registered FCM token for technician {id}", extra=log_extra)
    return {"status": "registered", "tech_id": id}


@router.post("/notifications/send-push", response_model=NotificationSendResponse)
async def send_push_notification(
    payload: NotificationSendRequest,
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    log_extra = {"correlation_id": correlation_id, "tenant_id": x_tenant_id, "job_id": payload.job_id}

    if not payload.tech_ids:
        raise HTTPException(status_code=400, detail="tech_ids list cannot be empty")

    if len(payload.tech_ids) > 50:
        raise HTTPException(status_code=400, detail="Cannot send to more than 50 technicians at once")

    # Fetch job details for notification title and body
    job = None
    if str(payload.job_id).isdigit():
        job = db.query(Job).filter(Job.id == int(payload.job_id)).first()

    if job:
        job_title = job.service_type
        location = job.location
    else:
        # Fallback if job is not in DB (e.g. testing with mock UUIDs)
        job_title = "New Assignment"
        location = "Customer Location"

    logger.info(f"Dispatching push notifications to {len(payload.tech_ids)} technicians", extra=log_extra)
    
    result = await send_job_assignment_notification(
        db=db,
        job_id=payload.job_id,
        job_title=job_title,
        location=location,
        tech_ids=payload.tech_ids,
        correlation_id=correlation_id
    )

    return result

@router.post("/notifications/send-sms", response_model=NotificationSendResponse)
async def send_sms_notification(
    payload: SMSSendRequest,
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    log_extra = {"correlation_id": correlation_id, "tenant_id": x_tenant_id, "job_id": payload.job_id}

    if not payload.tech_ids:
        raise HTTPException(status_code=400, detail="tech_ids list cannot be empty")

    job = None
    if str(payload.job_id).isdigit():
        job = db.query(Job).filter(Job.id == int(payload.job_id)).first()

    if job:
        job_title = job.service_type
        location = job.location
        priority = job.priority
    else:
        job_title = "New Assignment"
        location = "Customer Location"
        priority = "HIGH"

    logger.info(f"Dispatching SMS notifications to {len(payload.tech_ids)} technicians", extra=log_extra)
    
    result = await send_job_assignment_sms(
        db=db,
        job_id=payload.job_id,
        job_title=job_title,
        location=location,
        priority=priority,
        tech_ids=payload.tech_ids,
        correlation_id=correlation_id
    )

    return result

@router.post("/webhooks/twilio-status")
async def twilio_status_webhook(
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    ErrorCode: Optional[str] = Form(None),
    To: Optional[str] = Form(None),
    Price: Optional[float] = Form(None),
    db: Session = Depends(get_db)
):
    logger.info(f"Received Twilio Status Webhook: {MessageSid} - {MessageStatus}")
    delivery = db.query(SMSDelivery).filter(SMSDelivery.sms_sid == MessageSid).first()
    
    if delivery:
        delivery.status = MessageStatus
        if ErrorCode:
            delivery.error_message = f"ErrorCode: {ErrorCode}"
        if Price is not None:
            # Twilio's price is often negative, take absolute value for cost
            delivery.cost = abs(Price)
        db.commit()
    
    return {"status": "ok"}

@router.post("/webhooks/twilio-inbound")
async def twilio_inbound_webhook(
    MessageSid: str = Form(...),
    From: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db)
):
    # Ensure no PII in logs
    masked_from = f"+{'*'*(len(From)-5)}{From[-4:]}" if len(From) > 8 else "***"
    logger.info(f"Received Twilio Inbound Message from {masked_from}")
    
    # Check for STOP keyword
    if Body and Body.strip().upper() in ["STOP", "UNSUBSCRIBE", "CANCEL", "QUIT", "END"]:
        tech = db.query(Technician).filter(Technician.phone_number == From).first()
        if tech:
            tech.sms_opt_out = 1
            db.commit()
            logger.info(f"Technician {tech.tech_id} opted out of SMS notifications.")
            
    return {"status": "ok"}
