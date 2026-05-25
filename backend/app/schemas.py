from datetime import date, datetime
from typing import Literal, Optional, Union
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
        "contact_number"
    )
    @classmethod
    def not_empty(cls, value, info):
        if info.field_name == "required_skill" and value is None:
            return value
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
    tech_id: Optional[str] = None
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

class TechnicianStatusUpdate(BaseModel):
    technician_id: int
    status: str

class TechnicianResponse(BaseModel):
    technician_id: int
    tech_id: Optional[str] = None
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
    technician_id: int
    technician: str
    skill: str
    location: str
    status: str
    current_jobs: int
    max_jobs: int
    eligible_for_assignment: bool

    class Config:
        from_attributes = True


class TechnicianAssignment(BaseModel):
    job_id: Union[int, str]
    technician_id: Optional[int] = None
    job_type: Optional[str] = None


class NearestTechnicianResponse(BaseModel):
    technician: TechnicianResponse
    distance: float

class PlannedAssignmentResponse(BaseModel):
    job_id: int
    technician: str
    skill: str
    customer: str
    location: str
    priority: str
    status: str
    current_jobs: int
    max_jobs: int

    class Config:
        from_attributes = True


class HeartbeatPayload(BaseModel):
    last_lat: Optional[float] = None
    last_lng: Optional[float] = None


class AvailabilityResponse(BaseModel):
    tech_id: str
    status: str
    last_ping: datetime
    active_jobs: int
    last_lat: Optional[float] = None
    last_lng: Optional[float] = None

class DisqualifiedTechnician(BaseModel):
    tech_id: str
    name: str
    reason: str
    details: Optional[list[str]] = None
    message: str

class RankedTechnician(BaseModel):
    rank: int
    tech_id: str
    name: str
    proximity_score: float
    skill_score: float
    workload_score: float
    composite_score: float
    score_breakdown: Optional[dict] = None
    warnings: Optional[list[str]] = None
    distance_km: Optional[float] = None
    active_jobs: int
    max_capacity: int = 3
    is_top_3: bool = False
    is_recommended: bool = False
    estimated_arrival: Optional[str] = None

class ScoringWeights(BaseModel):
    proximity: float
    skill: float
    workload: float

class PlanResponse(BaseModel):
    job_id: str
    job_title: str
    status: str
    ranked_technicians: list[RankedTechnician]
    disqualified_technicians: list[DisqualifiedTechnician]
    scoring_weights: ScoringWeights
    cache_ttl_seconds: int

class FCMTokenRegistration(BaseModel):
    token: str
    device_type: Literal["android", "ios"]

class NotificationSendRequest(BaseModel):
    job_id: str
    tech_ids: list[str]

class NotificationSendResponse(BaseModel):
    sent: int
    failed: int
    delivery_ids: list[int]

class SMSSendRequest(BaseModel):
    job_id: str
    tech_ids: list[str]

class InAppNotificationResponse(BaseModel):
    id: str
    tech_id: str
    job_id: Optional[str] = None
    type: str
    title: str
    body: Optional[str] = None
    status: str
    action_url: Optional[str] = None
    action_type: Optional[str] = None
    priority: str
    created_at: datetime
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    notification_metadata: Optional[dict] = None

    class Config:
        from_attributes = True

class PaginatedNotificationsResponse(BaseModel):
    notifications: list[InAppNotificationResponse]
    unread_count: int
    total: int

class BatchReadRequest(BaseModel):
    notification_ids: list[str]

class TemplateCreate(BaseModel):
    name: str
    type: str
    channel: str
    locale: Optional[str] = "en"
    format: Optional[str] = "text"
    title_template: Optional[str] = None
    body_template: str

class TemplateResponse(TemplateCreate):
    id: int
    version: int
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True

class TemplatePreviewRequest(BaseModel):
    title_template: Optional[str] = None
    body_template: str
    mock_context: dict

class TemplatePreviewResponse(BaseModel):
    rendered_title: Optional[str] = None
    rendered_body: str

class NotificationPreferences(BaseModel):
    sms_enabled: bool = True
    push_enabled: bool = True
    inapp_enabled: bool = True
    email_enabled: bool = False

    @field_validator('sms_enabled', 'push_enabled', 'inapp_enabled', 'email_enabled', mode='before')
    @classmethod
    def require_at_least_one(cls, v, info):
        # We will do a model_validator for the whole object instead
        return v

    @classmethod
    def validate_minimum_channels(cls, values):
        if not values.get('sms_enabled') and not values.get('push_enabled') and not values.get('inapp_enabled'):
            raise ValueError("At least one notification channel must be enabled")
        return values

from pydantic import model_validator

class NotificationPreferencesInput(BaseModel):
    sms_enabled: bool
    push_enabled: bool
    inapp_enabled: bool
    email_enabled: Optional[bool] = False

    @model_validator(mode='after')
    def check_at_least_one(self) -> 'NotificationPreferencesInput':
        if not self.sms_enabled and not self.push_enabled and not self.inapp_enabled:
            raise ValueError("At least one notification channel must be enabled")
        return self

class PreferencesUpdateResponse(BaseModel):
    tech_id: str
    preferences: dict
    updated_at: datetime
    updated_by: str




