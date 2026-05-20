from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
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
    technician_location = Column(String(150), nullable=False)
    technician_status = Column(String(30), default="AVAILABLE")
    current_jobs = Column(Integer, default=0)
    max_jobs = Column(Integer, default=5)
    last_ping = Column(DateTime(timezone=True), nullable=True) # Added for heartbeat
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


from sqlalchemy import event

@event.listens_for(AuditEvent, "before_update")
def prevent_audit_event_update(mapper, connection, target):
    raise ValueError("AuditEvent is immutable")

@event.listens_for(AuditEvent, "before_delete")
def prevent_audit_event_delete(mapper, connection, target):
    raise ValueError("AuditEvent is immutable")