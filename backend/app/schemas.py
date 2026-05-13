from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, field_validator


class JobCreate(BaseModel):
    customer_name: str
    location: str
    issue_description: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL", "P1", "P2", "P3", "P4", "P5"] # Merged priorities
    service_type: str
    contact_number: str
    preferred_service_date: date
    required_skill: str # My addition
    status: str = "active"

    @field_validator(
        "customer_name",
        "location",
        "issue_description",
        "service_type",
        "contact_number",
        "required_skill"
    )
    @classmethod
    def not_empty(cls, value):
        if not value or not value.strip():
            raise ValueError("Field cannot be empty")
        return value

    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, value):
        if not value.isdigit() or len(value) != 10:
            raise ValueError("Contact number must be 10 digits")
        # Relaxed validation or check if it matches original
        return value


class JobResponse(BaseModel):
    id: int
    customer_name: str
    location: str
    issue_description: str
    priority: str
    service_type: str
    contact_number: str
    preferred_service_date: date
    status: str
    required_skill: Optional[str] = None
    assigned_technician_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TechnicianCreate(BaseModel):
    technician_name: str
    technician_skill: str
    technician_location: str
    technician_status: str

    @field_validator("technician_name", "technician_skill", "technician_location", "technician_status")
    @classmethod
    def field_must_not_be_empty(cls, value):
        if not value or not value.strip():
            raise ValueError("Field cannot be empty")
        return value.strip()


class TechnicianResponse(BaseModel):
    technician_id: int
    technician_name: str
    technician_skill: str
    technician_location: str
    technician_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TechnicianAssignment(BaseModel):
    job_id: int
    technician_id: int


class NearestTechnicianResponse(BaseModel):
    technician: TechnicianResponse
    distance: float