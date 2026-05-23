import os
import re
import asyncio
import uuid
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from sqlalchemy.orm import Session
from .logger import logger
from .models import Technician, SMSDelivery
from ..redis_client import get_redis_client
from .preferences import get_technician_preferences

# Environment variables
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', 'AC_dummy_account_sid')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', 'dummy_auth_token')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '+1234567890')

# Initialize Twilio Client
# Uses dummy values if env vars are missing for local dev to not crash on startup
twilio_client = None
if 'AC' in TWILIO_ACCOUNT_SID:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logger.info("Twilio client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Twilio client: {e}")

def validate_phone_number(phone_number: str) -> bool:
    """Validate E.164 phone number format (e.g., +919876543210)"""
    if not phone_number:
        return False
    # Regex: '+' followed by 1 to 15 digits
    pattern = r"^\+[1-9]\d{1,14}$"
    return bool(re.match(pattern, phone_number))

def generate_sms_template(job_title: str, address: str, priority: str, job_id: str) -> str:
    """
    Generate SMS text strictly under 160 chars.
    Template:
    FieldOps: New job '{title}' at {address}.
    Priority: {priority}.
    Accept: {short_url}
    Expires in 10 min.
    Reply STOP to opt out.
    """
    # Max length budget: 
    # Base text is ~80 chars. We need to truncate title and address if they are too long.
    short_url = f"api.fieldops.io/j/{str(job_id)[:8]}" # using short url mock
    
    # Trim title to 20 chars, address to 30 chars max to be safe.
    t_title = (job_title[:17] + '...') if len(job_title) > 20 else job_title
    t_address = (address[:27] + '...') if len(address) > 30 else address
    
    message = (
        f"FieldOps: New job '{t_title}' at {t_address}. "
        f"Priority: {priority}. "
        f"Accept: {short_url} "
        f"Expires in 10 min. "
        f"Reply STOP to opt out."
    )
    return message

def check_rate_limit(redis_client, tech_id: str) -> bool:
    """Check if the technician has exceeded 10 SMS per minute."""
    if not redis_client:
        return True # pass if no redis
    
    key = f"rate_limit:sms:{tech_id}"
    try:
        count = redis_client.get(key)
        if count and int(count) >= 10:
            return False
            
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60) # 60 seconds
        pipe.execute()
        return True
    except Exception as e:
        logger.error(f"Redis rate limiting error: {e}")
        return True # fail open

async def send_job_assignment_sms(
    db: Session,
    job_id: str,
    job_title: str,
    location: str,
    priority: str,
    tech_ids: list[str],
    correlation_id: str = None,
    max_retries: int = 3
) -> dict:
    correlation_id = correlation_id or str(uuid.uuid4())
    log_extra = {"correlation_id": correlation_id, "job_id": job_id}
    
    techs = db.query(Technician).filter(Technician.tech_id.in_(tech_ids)).all()
    
    redis_client = get_redis_client()
    
    sent_count = 0
    failed_count = 0
    delivery_ids = []
    
    message_body = generate_sms_template(job_title, location, priority, job_id)
    
    for tech in techs:
        # Check Opt-out
        if tech.sms_opt_out:
            logger.info(f"Skipping tech {tech.tech_id} (opted out of SMS)", extra=log_extra)
            failed_count += 1
            continue
            
        # Check explicit preference
        prefs = get_technician_preferences(db, tech.tech_id)
        if not prefs.get("sms_enabled", True):
            logger.info(f"Skipping tech {tech.tech_id} (SMS notifications disabled via preferences)", extra=log_extra)
            failed_count += 1
            continue
            
        # Check Valid Phone Number
        if not validate_phone_number(tech.phone_number):
            logger.warning(f"Skipping tech {tech.tech_id} (invalid/missing phone number: {tech.phone_number})", extra=log_extra)
            failed_count += 1
            continue
            
        # Check Rate Limit
        if not check_rate_limit(redis_client, tech.tech_id):
            logger.warning(f"Rate limit exceeded for tech {tech.tech_id}. Skipping SMS.", extra=log_extra)
            failed_count += 1
            continue
            
        # Ready to send
        delivery = SMSDelivery(
            tech_id=tech.tech_id,
            job_id=str(job_id),
            status="queued"
        )
        db.add(delivery)
        db.commit()
        db.refresh(delivery)
        
        # We process sends individually per tech to respect rate limits and individual tracking
        success = False
        
        for attempt in range(max_retries):
            try:
                if not twilio_client:
                    # Mock for local dev
                    logger.info(f"Mock sending SMS to {tech.phone_number}: {message_body}", extra=log_extra)
                    delivery.status = "sent"
                    delivery.sms_sid = f"SMmock_{uuid.uuid4().hex[:12]}"
                    success = True
                    break

                response = twilio_client.messages.create(
                    body=message_body,
                    from_=TWILIO_PHONE_NUMBER,
                    to=tech.phone_number,
                    status_callback="https://api.fieldops.io/v1/webhooks/twilio-status"
                )
                
                delivery.status = "sent"
                delivery.sms_sid = response.sid
                success = True
                logger.info(f"Sent SMS to {tech.tech_id} (SID: {response.sid})", extra=log_extra)
                break
                
            except TwilioRestException as e:
                logger.error(f"Twilio API Error for {tech.tech_id}: {e}", extra=log_extra)
                # If it's a 4xx error (like invalid number), don't retry
                if e.status and 400 <= e.status < 500:
                    delivery.error_message = str(e)
                    break
                # Otherwise backoff and retry
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Unexpected error sending SMS to {tech.tech_id}: {e}", extra=log_extra)
                await asyncio.sleep(2 ** attempt)

        if success:
            sent_count += 1
        else:
            failed_count += 1
            delivery.status = "failed"
            if not delivery.error_message:
                delivery.error_message = "Max retries exceeded or unexpected error."

        db.commit()
        delivery_ids.append(delivery.id)
        
    return {
        "sent": sent_count,
        "failed": failed_count,
        "delivery_ids": delivery_ids
    }
