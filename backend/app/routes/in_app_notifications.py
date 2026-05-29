from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid

from .dispatch import verify_jwt_token
from ..database import get_db
from ..models import Technician, InAppNotification
from ..schemas import InAppNotificationResponse, PaginatedNotificationsResponse, BatchReadRequest
from ..logger import logger
from ..services.socket_manager import emit_notification

router = APIRouter(
    tags=["In-App Notifications"]
)

@router.get("/technicians/{id}/notifications", response_model=PaginatedNotificationsResponse)
async def get_technician_notifications(
    id: str,
    status: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    # Verify tech exists
    tech = db.query(Technician).filter(Technician.tech_id == id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    query = db.query(InAppNotification).filter(
        InAppNotification.tech_id == id,
        InAppNotification.status != 'DISMISSED'
    )

    now = datetime.now(timezone.utc)
    # Filter out expired notifications
    query = query.filter(
        (InAppNotification.expires_at == None) | (InAppNotification.expires_at > now)
    )

    if status:
        query = query.filter(InAppNotification.status == status.upper())
        
    if type:
        query = query.filter(InAppNotification.type == type)

    total = query.count()
    
    notifications = query.order_by(desc(InAppNotification.created_at))\
                         .offset(offset)\
                         .limit(limit)\
                         .all()

    # Get global unread count
    unread_count = db.query(InAppNotification).filter(
        InAppNotification.tech_id == id,
        InAppNotification.status == 'UNREAD'
    ).count()

    return {
        "notifications": notifications,
        "unread_count": unread_count,
        "total": total
    }

@router.patch("/notifications/{id}/read")
async def mark_notification_read(
    id: str,
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    notification = db.query(InAppNotification).filter(InAppNotification.id == id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    if notification.status == 'UNREAD':
        notification.status = 'READ'
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        
    return {"status": "READ", "read_at": notification.read_at.isoformat() if notification.read_at else None}

@router.patch("/notifications/batch-read")
async def batch_mark_read(
    payload: BatchReadRequest,
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    if not payload.notification_ids:
        return {"updated": 0}
        
    updated = db.query(InAppNotification).filter(
        InAppNotification.id.in_(payload.notification_ids),
        InAppNotification.status == 'UNREAD'
    ).update({
        "status": "READ",
        "read_at": datetime.now(timezone.utc)
    }, synchronize_session=False)
    
    db.commit()
    return {"updated": updated}

@router.patch("/notifications/{id}/dismiss")
async def dismiss_notification(
    id: str,
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    notification = db.query(InAppNotification).filter(InAppNotification.id == id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notification.status = 'DISMISSED'
    notification.dismissed_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"status": "DISMISSED", "dismissed_at": notification.dismissed_at.isoformat() if notification.dismissed_at else None}

@router.delete("/notifications/system/cleanup", status_code=204)
async def cleanup_notifications(
    db: Session = Depends(get_db)
):
    # Auto-delete notifications older than 30 days
    threshold = datetime.now(timezone.utc) - timedelta(days=30)
    db.query(InAppNotification).filter(InAppNotification.created_at < threshold).delete(synchronize_session=False)
    db.commit()
    return None
