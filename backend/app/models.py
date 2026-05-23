from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, JSON, Float, CheckConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


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
    customer_name = Column(String(100), nullable=False)
    location = Column(String(150), nullable=False)
    issue_description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False)
    service_type = Column(String(50), nullable=False)
    contact_number = Column(String(15), nullable=False)
    preferred_service_date = Column(Date, nullable=False)
    required_skill = Column(String(100), nullable=True) # My addition
    status = Column(String(30), default="active")
    assigned_technician_id = Column(Integer, ForeignKey("technicians.technician_id"), nullable=True) # My addition
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    technician = relationship("Technician", back_populates="jobs")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    tech_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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