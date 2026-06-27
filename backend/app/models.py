from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, JSON, Float, CheckConstraint, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    parent_tenant_id = Column(String(50), ForeignKey("tenants.id"), nullable=True)


class Technician(Base):
    __tablename__ = "technicians"

    technician_id = Column(Integer, primary_key=True, index=True)
    tech_id = Column(String(36), unique=True, index=True, nullable=True) # Added for heartbeat UUID
    tenant_id = Column(String(50), index=True, nullable=True) # Added for tenant isolation
    technician_name = Column(String(100), nullable=False)
    technician_skill = Column(String(100), nullable=False)
    certifications_data = Column(JSON, nullable=True)
    technician_location = Column(String(150), nullable=False)
    technician_status = Column(String(30), default="AVAILABLE")
    current_jobs = Column(Integer, default=0)
    max_jobs = Column(Integer, default=5)
    last_ping = Column(DateTime(timezone=True), nullable=True) # Added for heartbeat
    fcm_token = Column(String(255), nullable=True) # Added for FCM
    device_type = Column(String(20), nullable=True) # 'android' or 'ios'
    phone_number = Column(String(20), nullable=True) # E.164 format
    sms_opt_out = Column(Integer, default=0) # 0 for false, 1 for true
    notification_preferences = Column(JSON, default={
        "sms_enabled": True,
        "push_enabled": True,
        "inapp_enabled": True,
        "email_enabled": False
    })
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    jobs = relationship("Job", back_populates="technician")


class Job(Base):
    __tablename__ = "jobs"  

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(50), index=True, nullable=True) # Added for tenant isolation
    customer_name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    issue_description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False)
    service_type = Column(String(50), nullable=False)
    contact_number = Column(String(15), nullable=False)
    preferred_service_date = Column(Date, nullable=False)
    required_skill = Column(String(100), nullable=True) # My addition
    status = Column(String(30), default="CREATED")
    assigned_technician_id = Column(Integer, ForeignKey("technicians.technician_id"), nullable=True) # My addition
    sla_deadline = Column(DateTime(timezone=True), nullable=True) # Added for SLA tracking
    attempt_count = Column(Integer, default=0)
    gps_active = Column(Boolean, default=False, nullable=False)
    work_report = Column(Text, nullable=True)
    customer_id = Column(String(50), nullable=True)
    customer_email = Column(String(100), nullable=True)
    geofence_radius = Column(Float, default=100.0, nullable=False)
    previous_priority = Column(String(20), nullable=True)
    bumped_at = Column(DateTime(timezone=True), nullable=True)
    site_latitude = Column(Float, nullable=True)
    site_longitude = Column(Float, nullable=True)
    site_address = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Transition timestamps
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    en_route_at = Column(DateTime(timezone=True), nullable=True)
    on_site_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Transition actors
    assigned_by = Column(String(50), nullable=True)
    en_route_by = Column(String(50), nullable=True)
    on_site_by = Column(String(50), nullable=True)
    completed_by = Column(String(50), nullable=True)
    cancelled_by = Column(String(50), nullable=True)
    closed_by = Column(String(50), nullable=True)

    # Reason fields
    cancellation_reason = Column(Text, nullable=True)
    closure_reason = Column(Text, nullable=True)

    technician = relationship("Technician", back_populates="jobs")

    @property
    def technician_id(self) -> Optional[str]:
        return str(self.assigned_technician_id) if self.assigned_technician_id is not None else None

    def transition(self, new_status, actor_id: str, actor_role: str, reason: str = None, is_override: bool = False) -> None:
        from .services.job_status_machine import transition_job
        transition_job(self, new_status, actor_id, actor_role, reason, is_override)



class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    tech_id = Column(String(36), nullable=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Fields required for job status transition audit trail
    job_id = Column(String(36), nullable=True, index=True)
    actor_id = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    correlation_id = Column(String(36), nullable=True)


class DispatcherNotification(Base):
    __tablename__ = "dispatcher_notifications"

    id = Column(Integer, primary_key=True, index=True)
    tech_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    tech_id = Column(String(36), nullable=False, index=True)
    job_id = Column(String(36), nullable=False, index=True)
    fcm_message_id = Column(String(255), nullable=True)
    status = Column(String(30), nullable=False, default="sent") # sent, delivered, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SMSDelivery(Base):
    __tablename__ = "sms_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    tech_id = Column(String(36), nullable=False, index=True)
    job_id = Column(String(36), nullable=False, index=True)
    sms_sid = Column(String(255), nullable=True)
    status = Column(String(30), nullable=False, default="queued") # queued, sent, delivered, failed, undelivered
    cost = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class InAppNotification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True) # Using UUID string for portability
    tech_id = Column(String(36), ForeignKey("technicians.tech_id"), nullable=False)
    job_id = Column(String(36), nullable=True) # Assuming jobs use string UUIDs in some contexts, or int
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    status = Column(String(20), default="UNREAD")
    action_url = Column(String(500), nullable=True)
    action_type = Column(String(50), nullable=True)
    priority = Column(String(20), default="NORMAL")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    notification_metadata = Column(JSON, default={})

    __table_args__ = (
        CheckConstraint("status IN ('UNREAD', 'READ', 'DISMISSED')", name="valid_status"),
        Index("idx_notifications_tech_status", "tech_id", "status"),
        Index("idx_notifications_created_at", "created_at"),
        Index("idx_notifications_type", "type"),
    )

class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False) # assignment, reminder, escalation
    channel = Column(String(20), nullable=False) # push, sms, in_app, email
    locale = Column(String(10), default="en") # en, hi, ta
    format = Column(String(20), default="text") # html, text
    title_template = Column(Text, nullable=True)
    body_template = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    is_active = Column(Integer, default=1) # 1 for True, 0 for False
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_template_lookup", "type", "channel", "locale", "is_active"),
    )

class PreferenceAuditLog(Base):
    __tablename__ = "preference_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tech_id = Column(String(36), nullable=False, index=True)
    updated_by = Column(String(50), nullable=False)
    old_preferences = Column(JSON, nullable=True)
    new_preferences = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SkillTaxonomy(Base):
    __tablename__ = "skill_taxonomy"

    id = Column(String(50), primary_key=True, default="default")
    taxonomy_data = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScoringConfiguration(Base):
    __tablename__ = "scoring_configurations"

    tenant_id = Column(String(50), primary_key=True, default="default")
    proximity_weight = Column(Float, default=0.4)
    skill_weight = Column(Float, default=0.4)
    workload_weight = Column(Float, default=0.2)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


from sqlalchemy import event

@event.listens_for(AuditEvent, "before_update")
def prevent_audit_event_update(mapper, connection, target):
    raise ValueError("AuditEvent is immutable")

@event.listens_for(AuditEvent, "before_delete")
def prevent_audit_event_delete(mapper, connection, target):
    raise ValueError("AuditEvent is immutable")

class SLAEscalation(Base):
    __tablename__ = "sla_escalations"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    manager_notified_at = Column(DateTime(timezone=True), nullable=True)
    manager_responded_at = Column(DateTime(timezone=True), nullable=True)
    cto_notified_at = Column(DateTime(timezone=True), nullable=True)
    action_taken = Column(String(100), nullable=True)
    status = Column(String(50), default="ESCALATED")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DispatcherAlert(Base):
    __tablename__ = "dispatcher_alerts"

    id = Column(String(36), primary_key=True)
    type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    attempt_count = Column(Integer, nullable=False)
    max_attempts = Column(Integer, nullable=False)
    excluded_technicians = Column(JSON, nullable=True)
    recommended_action = Column(Text, nullable=True)
    acknowledged = Column(Integer, default=0) # 0 for false, 1 for true
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OverrideAuditEvent(Base):
    __tablename__ = "override_audit_events"

    id = Column(String(36), primary_key=True)
    event_type = Column(String(50), nullable=False, default="manual_override")
    actor_id = Column(String(36), nullable=False, index=True)
    actor_role = Column(String(50), nullable=False)
    actor_name = Column(String(200), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    
    before_state = Column(JSON, nullable=False)
    after_state = Column(JSON, nullable=False)
    
    justification = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    correlation_id = Column(String(36), nullable=True)
    
    tenant_id = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

@event.listens_for(OverrideAuditEvent, "before_update")
def prevent_override_audit_event_update(mapper, connection, target):
    raise ValueError("OverrideAuditEvent is immutable (BR-009)")

@event.listens_for(OverrideAuditEvent, "before_delete")
def prevent_override_audit_event_delete(mapper, connection, target):
    raise ValueError("OverrideAuditEvent is immutable (BR-009)")


class AssignmentOverride(Base):
    __tablename__ = "assignment_overrides"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    actor_name = Column(String(100), nullable=False)
    actor_role = Column(String(30), nullable=False)
    justification = Column(Text, nullable=False)
    previous_technician_id = Column(Integer, ForeignKey("technicians.technician_id"), nullable=True)
    previous_technician_name = Column(String(100), nullable=True)
    new_technician_id = Column(Integer, ForeignKey("technicians.technician_id"), nullable=False)
    new_technician_name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GPSPing(Base):
    __tablename__ = "gps_pings"

    id = Column(String(36), primary_key=True)
    technician_id = Column(String(36), ForeignKey("technicians.tech_id"), nullable=False, index=True)
    job_id = Column(String(36), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    accuracy = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    correlation_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TenantGPSConfiguration(Base):
    __tablename__ = "tenant_gps_configurations"

    tenant_id = Column(String(50), primary_key=True, index=True)
    retention_days = Column(Integer, nullable=False, default=30)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("retention_days BETWEEN 1 AND 90", name="valid_retention_days"),
    )


class GPSPurgeAuditLog(Base):
    __tablename__ = "gps_purge_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), nullable=False, index=True)
    job_id = Column(String(36), nullable=True, index=True)
    purge_type = Column(String(20), nullable=False)  # 'age_based', 'event_based', 'manual'
    deleted_count = Column(Integer, nullable=False)
    correlation_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class GPSRejectedPingLog(Base):
    __tablename__ = "gps_rejected_ping_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    technician_id = Column(String(50), nullable=True, index=True)
    job_id = Column(String(36), nullable=True, index=True)
    reason = Column(String(200), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    tenant_id = Column(String(50), nullable=True, index=True)


@event.listens_for(Job, 'after_update')
def on_job_status_changed(mapper, connection, target):
    from sqlalchemy import inspect
    state = inspect(target)
    history = state.get_history('status', True)
    if history.has_changes():
        new_status = history.added[0] if history.added else None
        old_status = history.deleted[0] if history.deleted else None
        
        from .database import SessionLocal
        from .redis_client import get_redis_client
        from .context import correlation_id_ctx
        import threading
        import time

        job_id = target.id
        tenant_id = target.tenant_id or "tenant-1"
        correlation_id = correlation_id_ctx.get() or None

        # Store transition start time in Redis for SLA tracking
        try:
            redis_client = get_redis_client()
            if redis_client:
                redis_client.set(f"gps_purge_start_time:{job_id}", str(time.time()), ex=3600)
        except Exception:
            pass

        # Trigger GPS Purge if terminal
        if new_status and str(new_status).upper().strip() in ["CLOSED", "CANCELLED", "CANCELED"]:
            from .tasks import purge_job_gps_data_task, execute_job_gps_purge_sync
            try:
                purge_job_gps_data_task.delay(job_id, tenant_id, "event_based", correlation_id)
            except Exception:
                def run_purge_in_thread():
                    db = SessionLocal()
                    try:
                        execute_job_gps_purge_sync(db, job_id, tenant_id, "event_based", correlation_id)
                    finally:
                        db.close()
                threading.Thread(target=run_purge_in_thread).start()

        # Trigger transition processing (notifications, SLA, events)
        from .tasks import process_job_status_transition_task
        actor_id = getattr(target, "_actor_id", "system")
        actor_role = getattr(target, "_actor_role", "system")
        reason = getattr(target, "_transition_reason", None)
        try:
            process_job_status_transition_task.delay(
                job_id, old_status, new_status, actor_id, actor_role, reason, correlation_id
            )
        except Exception:
            def run_transition_in_thread():
                db = SessionLocal()
                try:
                    process_job_status_transition_task(
                        job_id, old_status, new_status, actor_id, actor_role, reason, correlation_id
                    )
                finally:
                    db.close()
            threading.Thread(target=run_transition_in_thread).start()


class ETAHistory(Base):
    __tablename__ = "eta_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    eta = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Float, nullable=False)
    distance_km = Column(Float, nullable=False)
    traffic_delay_minutes = Column(Float, default=0.0)
    source_ping_id = Column(String(36), ForeignKey("gps_pings.id"), nullable=False, index=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    tenant_id = Column(String(50), nullable=False, index=True)


@event.listens_for(GPSPing, "after_insert")
def on_new_gps_ping(mapper, connection, target):
    job_id_int = int(target.job_id) if str(target.job_id).isdigit() else None
    if not job_id_int:
        return

    from sqlalchemy import select
    from .database import SessionLocal

    # Check job status
    job = connection.execute(
        select(Job).where(Job.id == job_id_int)
    ).fetchone()

    # Run geofence check
    from .services.geofence_monitor import GeofenceMonitor
    db = SessionLocal()
    try:
        monitor = GeofenceMonitor()
        monitor.process_ping(db, target)
    except Exception as e:
        logger.error(f"Failed to check geofence on new GPS ping: {e}")
    finally:
        db.close()

    if not job or str(job.status).upper().strip() not in ["ASSIGNED", "EN_ROUTE", "ON_SITE"]:
        return

    # Check throttle
    throttle_key = f"eta:throttle:{job_id_int}"
    from .redis_client import get_redis_client
    redis = get_redis_client()
    if redis:
        try:
            if redis.get(throttle_key):
                return
            # Set throttle key with 30s TTL
            redis.setex(throttle_key, 30, "1")
            
            # Invalidate old ETA cache
            redis.delete(f"eta:{target.technician_id}:{job_id_int}")
            redis.delete(f"eta:fallback:{target.technician_id}:{job_id_int}")
        except Exception:
            pass

    # Queue async recalculation
    from .tasks import update_eta_task
    from .context import correlation_id_ctx
    correlation_id = correlation_id_ctx.get() or None
    try:
        update_eta_task.delay(
            technician_id=target.technician_id,
            job_id=job_id_int,
            ping_id=target.id,
            correlation_id=correlation_id
        )
    except Exception:
        import threading
        from .database import SessionLocal
        def run_in_thread():
            db = SessionLocal()
            try:
                update_eta_task(target.technician_id, job_id_int, target.id, correlation_id)
            finally:
                db.close()
        threading.Thread(target=run_in_thread).start()


class SecurityAuditLog(Base):
    __tablename__ = "security_audit_logs"

    id = Column(String(36), primary_key=True)
    event = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    severity = Column(String(20), nullable=False)
    user_tenant = Column(String(50), nullable=True, index=True)
    attempted_channel = Column(String(200), nullable=True)
    ip_address = Column(String(50), nullable=True)
    websocket_id = Column(String(50), nullable=True)
    action_taken = Column(String(50), nullable=True)
    payload_tenant = Column(String(50), nullable=True, index=True)
    target_tenant = Column(String(50), nullable=True, index=True)
    technician_id = Column(String(50), nullable=True)
    job_id = Column(String(50), nullable=True)
    tenant_id = Column(String(50), nullable=True, index=True)
