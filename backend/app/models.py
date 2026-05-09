from sqlalchemy import Column, Integer, String, Text, Date, DateTime
from sqlalchemy.sql import func
from app.database import Base


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
    status = Column(String(30), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())