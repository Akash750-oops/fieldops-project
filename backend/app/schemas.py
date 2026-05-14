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
    required_skill: Optional[str] = None # Made optional to match frontend
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
    customer_name: Optional[str] = None
    location: Optional[str] = None
    issue_description: Optional[str] = None
    priority: Optional[str] = None
    service_type: Optional[str] = None
    contact_number: Optional[str] = None
    preferred_service_date: Optional[date] = None
    status: Optional[str] = None
    required_skill: Optional[str] = None
    assigned_technician_id: Optional[int] = None
    created_at: Optional[datetime] = None
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


class TechnicianAvailabilityUpdate(BaseModel):
    technician_status: Literal["Available", "Busy", "Offline"]

class TechnicianResponse(BaseModel):
    technician_id: int
    technician_name: str
    technician_skill: str
    technician_location: str
    technician_status: str
    current_jobs: int
    max_jobs: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkloadResponse(BaseModel):
    technician: str
    current_jobs: int
    status: str


class WorkloadUpdate(BaseModel):
    technician_id: int
    current_jobs: int


class WorkloadValidationResponse(BaseModel):
    technician: str
    current_jobs: int
    max_jobs: int
    can_assign: bool
    message: str


class AvailableTechnicianResponse(BaseModel):
    technician: str
    status: str
    eligible_for_assignment: bool


class TechnicianAssignment(BaseModel):
    job_id: int
    technician_id: int


class NearestTechnicianResponse(BaseModel):
    technician: TechnicianResponse
    distance: float