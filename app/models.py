from sqlalchemy import Column, Integer, Text, TIMESTAMP, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base






class Technician(Base):
    __tablename__ = "technicians"

    technician_id = Column(Integer, primary_key=True, index=True)
    technician_name = Column(Text, nullable=False)
    technician_skill = Column(Text, nullable=False)
    technician_location = Column(Text, nullable=False)
    technician_status = Column(Text, nullable=False, server_default="AVAILABLE")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    jobs = relationship("Job", back_populates="technician")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    issue = Column(Text, nullable=False)
    priority = Column(Text, nullable=False)
    required_skill = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="active")
    assigned_technician_id = Column(Integer, ForeignKey("technicians.technician_id"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    technician = relationship("Technician", back_populates="jobs")