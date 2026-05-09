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
    skill: str
    phone_number: str
    availability_status: str
    assigned_area: str

    @field_validator("technician_name", "skill", "phone_number", "availability_status", "assigned_area")
    @classmethod
    def field_must_not_be_empty(cls, value):
        if value is None or value.strip() == "":
            raise ValueError("Field cannot be empty")
        return value.strip()

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value):
        if len(value) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        if not value.isdigit():
            raise ValueError("Phone number must contain only digits")
        return value


class TechnicianResponse(BaseModel):
    id: int
    technician_name: str
    skill: str
    phone_number: str
    availability_status: str
    assigned_area: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True