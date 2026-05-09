from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, field_validator


class JobCreate(BaseModel):
    customer_name: str
    location: str
    issue_description: str
    priority: Literal["P1", "P2", "P3", "P4", "P5"]
    service_type: str
    contact_number: str
    preferred_service_date: date

    @field_validator(
        "customer_name",
        "location",
        "issue_description",
        "service_type",
        "contact_number"
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
        if value[0] not in ["6", "7", "8", "9"]:
            raise ValueError("Enter a valid Indian mobile number")
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
    created_at: datetime

    class Config:
        from_attributes = True