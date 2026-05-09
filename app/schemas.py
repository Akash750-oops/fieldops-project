from pydantic import BaseModel, field_validator
from typing import Literal
from datetime import datetime


class JobCreate(BaseModel):
    customer_name: str
    location: str
    issue: str
    priority: str
    status: Literal["active", "pending", "in progress", "completed"] = "active"

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value):
        allowed = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if value not in allowed:
            raise ValueError("Invalid priority value")
        return value

    @field_validator("customer_name", "location", "issue")
    @classmethod
    def field_must_not_be_empty(cls, value):
        if value is None or value.strip() == "":
            raise ValueError("Field cannot be empty")
        return value.strip()


class JobResponse(BaseModel):
    id: int
    customer_name: str
    location: str
    issue: str
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime

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
        if value is None or value.strip() == "":
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