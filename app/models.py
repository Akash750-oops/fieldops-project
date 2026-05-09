from sqlalchemy import Column, Integer, Text, TIMESTAMP, CheckConstraint
from sqlalchemy.sql import func
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    issue = Column(Text, nullable=False)
    priority = Column(Text, nullable=False)
    status = Column(Text, default="active")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="check_priority_valid"
        ),
    )


class Technician(Base):
    __tablename__ = "technicians"

    technician_id = Column(Integer, primary_key=True, index=True)
    technician_name = Column(Text, nullable=False)
    technician_skill = Column(Text, nullable=False)
    technician_location = Column(Text, nullable=False)
    technician_status = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())