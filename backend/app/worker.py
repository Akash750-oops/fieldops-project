from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
import json

from .database import SessionLocal
from .models import Technician, AuditEvent, DispatcherNotification, InAppNotification
from .redis_client import get_redis_client
from .logger import logger

scheduler = BackgroundScheduler()

def check_technician_heartbeats():
    db = SessionLocal()
    redis_client = get_redis_client()
    
    try:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(seconds=120)
        
        # Determine if we are running against SQLite or PostgreSQL
        # SQLite doesn't handle timezone-aware datetime comparison in the same way.
        # We can detect engine and adjust threshold if needed.
        bind_engine = db.get_bind()
        is_sqlite = bind_engine.url.drivername.startswith("sqlite")
        
        query_threshold = threshold
        if is_sqlite:
            # SQLite stores datetime as naive text/int usually, so make threshold naive
            query_threshold = threshold.replace(tzinfo=None)

        # Query technicians with last_ping > 120s old and status in AVAILABLE or BUSY
        # Note: we compare last_ping < query_threshold
        techs = db.query(Technician).filter(
            Technician.last_ping < query_threshold,
            func.upper(Technician.technician_status).in_(['AVAILABLE', 'BUSY'])
        ).all()
        
        offline_count = 0
        
        for tech in techs:
            old_status = tech.technician_status
            
            # Handle edge case: technician has active jobs (BUSY preserved)
            if tech.current_jobs > 0:
                if old_status.upper() == 'BUSY':
                    new_status = 'BUSY'
                    message = f"Technician {tech.technician_name} (ID: {tech.tech_id}) missed heartbeat but has active jobs. Status preserved as BUSY."
                    notification = DispatcherNotification(
                        tech_id=tech.tech_id,
                        tenant_id=tech.tenant_id or "unknown",
                        message=message
                    )
                    db.add(notification)
                    logger.warning(message, extra={"tech_id": tech.tech_id, "tenant_id": tech.tenant_id})
                else:
                    # If AVAILABLE but has active jobs (abnormal state), we update to OFFLINE and notify
                    tech.technician_status = 'OFFLINE'
                    new_status = 'OFFLINE'
                    message = f"Technician {tech.technician_name} (ID: {tech.tech_id}) has active jobs but went OFFLINE due to missing heartbeat."
                    notification = DispatcherNotification(
                        tech_id=tech.tech_id,
                        tenant_id=tech.tenant_id or "unknown",
                        message=message
                    )
                    db.add(notification)
                    logger.warning(message, extra={"tech_id": tech.tech_id, "tenant_id": tech.tenant_id})
                    offline_count += 1
            else:
                # No active jobs: update to OFFLINE
                tech.technician_status = 'OFFLINE'
                new_status = 'OFFLINE'
                offline_count += 1
                
            if new_status != old_status:
                # Add audit log entry (immutable)
                audit = AuditEvent(
                    tech_id=tech.tech_id,
                    tenant_id=tech.tenant_id or "unknown",
                    event_type="STATUS_CHANGE",
                    old_status=old_status,
                    new_status=new_status
                )
                db.add(audit)
                
                # Invalidate Redis cache on status change to OFFLINE
                if redis_client and new_status == 'OFFLINE':
                    cache_key = f"tech:availability:{tech.tenant_id}:{tech.tech_id}"
                    redis_client.delete(cache_key)
            
            # Save progress for this technician
            db.commit()
            
        # Add metrics: OFFLINE events per hour
        if offline_count > 0 and redis_client:
            hour_str = now.strftime("%Y-%m-%d-%H")
            metric_key = f"metrics:offline_events:{hour_str}"
            try:
                redis_client.incr(metric_key, offline_count)
                redis_client.expire(metric_key, 7200) # 2 hours TTL
            except Exception as e:
                logger.error(f"Failed to update metrics: {e}")
                
        # Alerting for mass OFFLINE events
        if offline_count >= 5:
            logger.critical(
                f"ALERT: Mass OFFLINE event detected! {offline_count} technicians marked OFFLINE in a single run.",
                extra={"offline_count": offline_count}
            )
            
    except Exception as e:
        logger.error(f"Error in background heartbeat check job: {e}")
        db.rollback()
    finally:
        db.close()

def cleanup_old_notifications():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=30)
        
        updated = db.query(InAppNotification).filter(
            InAppNotification.created_at < threshold,
            InAppNotification.status != 'DISMISSED'
        ).update({
            "status": "DISMISSED",
            "dismissed_at": now
        }, synchronize_session=False)
        
        db.commit()
        if updated > 0:
            logger.info(f"Cleaned up {updated} old in-app notifications (soft deleted).")
    except Exception as e:
        logger.error(f"Error in background notification cleanup job: {e}")
        db.rollback()
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(check_technician_heartbeats, 'interval', seconds=60, id='heartbeat_checker')
        scheduler.add_job(cleanup_old_notifications, 'cron', hour=0, minute=0, id='notification_cleanup')
        scheduler.start()
        logger.info("Background heartbeat scheduler started.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background heartbeat scheduler stopped.")
