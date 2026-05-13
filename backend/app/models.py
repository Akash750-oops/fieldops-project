from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Technician(Base):
    __tablename__ = "technicians"

    technician_id = Column(Integer, primary_key=True, index=True)
    technician_name = Column(String(100), nullable=False)
    technician_skill = Column(String(100), nullable=False)
    technician_location = Column(String(150), nullable=False)
    technician_status = Column(String(30), default="AVAILABLE")
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