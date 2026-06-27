from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any
import json
import uuid
import logging
import asyncio

from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import AuditEvent, Technician, InAppNotification, Job
from ..redis_client import get_redis_client
from ..context import correlation_id_ctx
from .preferences import get_technician_preferences

logger = logging.getLogger(__name__)

@dataclass
class JobStatusEvent:
    job_id: str
    tenant_id: str
    from_status: str
    to_status: str
    actor_id: str
    actor_role: str
    reason: Optional[str]
    timestamp: datetime
    job_title: str
    job_location: str
    technician_id: Optional[str]
    technician_name: Optional[str]
    customer_id: Optional[str]
    customer_name: Optional[str]
    customer_phone: Optional[str]
    customer_email: Optional[str]
    eta: Optional[str]
    notification_channels: list[str]
    event_type: str = "job_status_changed"


class SendGridService:
    def __init__(self, api_key: str = None):
        import os
        self.api_key = api_key or os.getenv("SENDGRID_API_KEY", "SG.mock_key")
        
    async def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        import os
        # Check environment and key
        if not self.api_key or "mock" in self.api_key or not os.getenv("SENDGRID_API_KEY"):
            logger.info(f"[SendGrid Mock] Sending email to {to_email} with subject: {subject} body: {html_content}")
            return True
            
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email=os.getenv("SENDGRID_FROM_EMAIL", "no-reply@fieldops.io"),
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            sg = SendGridAPIClient(self.api_key)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, sg.send, message)
            logger.info(f"SendGrid email sent to {to_email}, status_code={response.status_code}")
            return response.status_code in (200, 201, 202)
        except Exception as e:
            logger.error(f"SendGrid failed to send email: {e}")
            return False


class EventPublisher:
    def __init__(self, redis_client=None):
        self.redis = redis_client or get_redis_client()
        self.channel = "events:job_status_changed"
    
    async def publish(self, event: JobStatusEvent) -> None:
        payload_dict = {
            "event_type": event.event_type,
            "job_id": event.job_id,
            "tenant_id": event.tenant_id,
            "from_status": event.from_status,
            "to_status": event.to_status,
            "actor_id": event.actor_id,
            "actor_role": event.actor_role,
            "reason": event.reason,
            "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp),
            "job_title": event.job_title,
            "job_location": event.job_location,
            "technician_id": event.technician_id,
            "technician_name": event.technician_name,
            "customer_id": event.customer_id,
            "customer_name": event.customer_name,
            "eta": event.eta,
            "notification_channels": event.notification_channels,
        }
        
        # Publish to Redis pub/sub
        if self.redis:
            try:
                self.redis.publish(self.channel, json.dumps(payload_dict))
                logger.info(f"Published status event to Redis channel {self.channel} for job {event.job_id}")
            except Exception as e:
                logger.error(f"Failed to publish status event to Redis: {e}")
        
        # Write to audit_events table
        await self._write_audit(event)
    
    async def _write_audit(self, event: JobStatusEvent) -> None:
        db = SessionLocal()
        try:
            audit_record = AuditEvent(
                event_type="job_status_transition",
                tech_id=event.technician_id or "system",
                tenant_id=event.tenant_id,
                old_status=event.from_status,
                new_status=event.to_status,
                reason=event.reason,
                job_id=event.job_id,
                actor_id=event.actor_id,
                details={
                    "from_status": event.from_status,
                    "to_status": event.to_status,
                    "reason": event.reason,
                    "job_title": event.job_title,
                    "technician_id": event.technician_id,
                    "notification_channels": event.notification_channels,
                },
                timestamp=event.timestamp,
                correlation_id=correlation_id_ctx.get() or None,
            )
            db.add(audit_record)
            db.commit()
            logger.info(f"Written AuditEvent for transition to {event.to_status} of job {event.job_id}")
        except Exception as e:
            logger.error(f"Failed to write AuditEvent for transition: {e}")
            db.rollback()
        finally:
            db.close()


class NotificationRouter:
    STATUS_NOTIFICATIONS = {
        "ASSIGNED": {
            "technician": {
                "channels": ["push", "sms"],
                "template": "job_assigned",
                "priority": "high",
            },
            "dispatcher": {
                "channels": ["in_app"],
                "template": "dispatcher_job_assigned",
                "priority": "normal",
                "batch": True,
            },
        },
        "EN_ROUTE": {
            "technician": {
                "channels": ["push"],
                "template": "journey_started",
                "priority": "normal",
            },
            "customer": {
                "channels": ["push", "sms"],
                "template": "technician_en_route",
                "priority": "high",
                "include_eta": True,
            },
            "dispatcher": {
                "channels": ["in_app"],
                "template": "dispatcher_en_route",
                "priority": "normal",
                "batch": True,
            },
        },
        "ON_SITE": {
            "technician": {
                "channels": ["push"],
                "template": "arrived_on_site",
                "priority": "normal",
            },
            "customer": {
                "channels": ["push", "sms"],
                "template": "technician_arrived",
                "priority": "high",
            },
            "dispatcher": {
                "channels": ["in_app"],
                "template": "dispatcher_on_site",
                "priority": "normal",
                "batch": True,
            },
        },
        "COMPLETED": {
            "technician": {
                "channels": ["push"],
                "template": "job_completed",
                "priority": "normal",
            },
            "customer": {
                "channels": ["push", "email"],
                "template": "job_done_survey",
                "priority": "normal",
                "include_survey_link": True,
            },
            "dispatcher": {
                "channels": ["in_app"],
                "template": "dispatcher_completed",
                "priority": "normal",
                "batch": True,
            },
        },
        "CANCELLED": {
            "technician": {
                "channels": ["push", "sms"],
                "template": "job_cancelled",
                "priority": "high",
            },
            "customer": {
                "channels": ["push", "sms", "email"],
                "template": "job_cancelled_customer",
                "priority": "high",
            },
            "dispatcher": {
                "channels": ["in_app", "email"],
                "template": "dispatcher_cancelled",
                "priority": "high",
                "batch": False,
            },
        },
    }
    
    def __init__(self, fcm_service=None, sms_service=None, email_service=None, ws_manager=None, redis_client=None):
        from .fcm import send_job_assignment_notification
        from .twilio_sms import send_job_assignment_sms
        from .socket_manager import ws_manager as default_ws_manager
        
        self.fcm = fcm_service or send_job_assignment_notification
        self.sms = sms_service or send_job_assignment_sms
        self.email = email_service or SendGridService()
        self.ws = ws_manager or default_ws_manager
        self.redis = redis_client or get_redis_client()
    
    async def route(self, event: JobStatusEvent) -> None:
        routing = self.STATUS_NOTIFICATIONS.get(event.to_status, {})
        
        for recipient_type, config in routing.items():
            # Check user preferences
            if not await self._check_preferences(event, recipient_type):
                continue
            
            # Build notification payload
            payload = self._build_payload(event, recipient_type, config)
            
            # Send via each channel
            for channel in config["channels"]:
                event.notification_channels.append(channel)
                if channel == "push":
                    await self._send_push(event, recipient_type, payload, config["priority"])
                elif channel == "sms":
                    await self._send_sms(event, recipient_type, payload)
                elif channel == "email":
                    await self._send_email(event, recipient_type, payload)
                elif channel == "in_app":
                    await self._send_in_app(event, recipient_type, payload, config.get("batch", False))
    
    def _build_payload(self, event: JobStatusEvent, recipient_type: str, config: dict) -> dict:
        base = {
            "job_id": event.job_id,
            "job_title": event.job_title,
            "job_location": event.job_location,
            "status": event.to_status,
            "timestamp": event.timestamp.isoformat() if hasattr(event.timestamp, "isoformat") else str(event.timestamp),
            "deep_link": f"https://fieldops.io/jobs/{event.job_id}",
        }
        
        if recipient_type == "technician":
            base["technician_name"] = event.technician_name
        elif recipient_type == "customer":
            base["customer_name"] = event.customer_name
            if config.get("include_eta"):
                base["eta"] = event.eta or "calculating..."
            if config.get("include_survey_link"):
                base["survey_link"] = f"https://fieldops.io/survey/{event.job_id}"
        elif recipient_type == "dispatcher":
            base["actor_name"] = event.actor_id
        
        return base
    
    async def _check_preferences(self, event: JobStatusEvent, recipient_type: str) -> bool:
        if recipient_type == "technician" and event.technician_id:
            db = SessionLocal()
            try:
                tech = db.query(Technician).filter(Technician.tech_id == event.technician_id).first()
                if tech:
                    # check opt out settings
                    # If the status requires SMS, we check sms_opt_out
                    routing = self.STATUS_NOTIFICATIONS.get(event.to_status, {}).get("technician", {})
                    channels = routing.get("channels", [])
                    
                    if "sms" in channels and tech.sms_opt_out == 1:
                        logger.info(f"Tech {tech.tech_id} has opted out of SMS notifications.")
                        # SMS is disabled, but other channels might be allowed, let's keep routing but sms skipped inside sender
                    
                    # check preferences dictionary
                    prefs = get_technician_preferences(db, tech.tech_id)
                    # if they turned off all notification preferences, we honor it
                    if not prefs.get("sms_enabled", True) and not prefs.get("push_enabled", True) and not prefs.get("inapp_enabled", True):
                        return False
            finally:
                db.close()
        return True
    
    async def _send_push(self, event: JobStatusEvent, recipient_type: str, payload: dict, priority: str):
        target_id = event.technician_id if recipient_type == "technician" else event.customer_id
        if not target_id:
            logger.warning(f"Push skipped: missing ID for recipient_type {recipient_type}")
            # If FCM token is missing, functional requirements say: fallback to SMS!
            if "sms" not in self.STATUS_NOTIFICATIONS.get(event.to_status, {}).get(recipient_type, {}).get("channels", []):
                await self._send_sms(event, recipient_type, payload)
            return

        db = SessionLocal()
        try:
            # Look up FCM token
            token = None
            if recipient_type == "technician":
                tech = db.query(Technician).filter(Technician.tech_id == target_id).first()
                if tech:
                    token = tech.fcm_token
            
            if token:
                # Call FCM service
                # Since FCM service accepts list of tech_ids, we can call it or wrap it
                # Note: fcm.py takes a list of tech_ids
                # In tests, fcm_service is mocked/patched, so we can call send_job_assignment_notification directly
                try:
                    await self.fcm(db, event.job_id, event.job_title, event.job_location, [target_id], correlation_id_ctx.get())
                except Exception as e:
                    logger.error(f"FCM push send failed: {e}")
            else:
                logger.warning(f"Push skipped: missing FCM token for {recipient_type} {target_id}. Falling back to SMS.")
                if "sms" not in self.STATUS_NOTIFICATIONS.get(event.to_status, {}).get(recipient_type, {}).get("channels", []):
                    await self._send_sms(event, recipient_type, payload)
        finally:
            db.close()

    async def _send_sms(self, event: JobStatusEvent, recipient_type: str, payload: dict):
        db = SessionLocal()
        try:
            if recipient_type == "technician" and event.technician_id:
                await self.sms(db, event.job_id, event.job_title, event.job_location, "HIGH", [event.technician_id], correlation_id_ctx.get())
            elif recipient_type == "customer" and event.customer_phone:
                # For customer SMS, since we do not have customer model, we can invoke the Twilio client directly or simulate
                from .twilio_sms import twilio_client, TWILIO_PHONE_NUMBER
                message_body = f"FieldOps alert: Customer {event.customer_name}, your job status is now {event.to_status}."
                if event.to_status == "EN_ROUTE":
                    message_body += f" ETA is {event.eta}."
                
                if twilio_client:
                    try:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None,
                            lambda: twilio_client.messages.create(
                                body=message_body,
                                from_=TWILIO_PHONE_NUMBER,
                                to=event.customer_phone
                            )
                        )
                        logger.info(f"Customer SMS sent to {event.customer_phone}")
                    except Exception as e:
                        logger.error(f"Customer SMS delivery failed: {e}")
                else:
                    logger.info(f"[SMS Mock] Customer SMS to {event.customer_phone}: {message_body}")
        finally:
            db.close()

    async def _send_email(self, event: JobStatusEvent, recipient_type: str, payload: dict):
        email_to = None
        if recipient_type == "customer":
            email_to = event.customer_email
        
        if email_to:
            subject = f"FieldOps Job Status Update: {event.to_status}"
            body_html = f"<p>Dear {event.customer_name or 'Valued Customer'},</p>"
            body_html += f"<p>Your job '{event.job_title}' at {event.job_location} is now <strong>{event.to_status}</strong>.</p>"
            if event.to_status == "COMPLETED":
                body_html += f"<p>Please complete our service survey: <a href='https://fieldops.io/survey/{event.job_id}'>Take Survey</a></p>"
            
            await self.email.send_email(email_to, subject, body_html)

    async def _send_in_app(self, event: JobStatusEvent, recipient_type: str, payload: dict, batch: bool):
        if recipient_type == "dispatcher":
            if batch:
                if self.redis:
                    try:
                        self.redis.lpush(
                            f"dispatcher_digest:{event.tenant_id}",
                            json.dumps(payload)
                        )
                        logger.info(f"Queued dispatcher notification to digest for tenant {event.tenant_id}")
                    except Exception as e:
                        logger.error(f"Failed to queue dispatcher digest: {e}")
            else:
                # Immediate broadcast
                try:
                    await self.ws.broadcast(
                        f"tenant:{event.tenant_id}:dispatchers",
                        {
                            "type": "notification",
                            "payload": payload,
                        }
                    )
                    logger.info(f"Broadcasted immediate dispatcher notification for tenant {event.tenant_id}")
                except Exception as e:
                    logger.error(f"Failed to broadcast immediate dispatcher notification: {e}")
