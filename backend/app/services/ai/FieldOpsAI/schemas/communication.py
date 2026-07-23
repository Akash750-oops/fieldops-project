"""
communication.py

Pydantic schemas for the FieldOps Communication Agent.

The Communication Agent generates recipient-facing content for:

- Email
- SMS
- Push notifications
- In-app notifications

The agent only generates content.

It never:

- Sends notifications
- Updates the database
- Changes job status
- Assigns technicians
- Promises unsupported business actions
"""

from __future__ import annotations

from typing import Any, Literal, Self
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
    field_validator,
)
from app.services.ai.FieldOpsAI.services.prompt_locale_service import normalize_locale, InvalidLocaleError


# ==========================================================
# Shared Types
# ==========================================================


CommunicationChannel = Literal[
    "EMAIL",
    "SMS",
    "PUSH",
    "IN_APP",
]


class CommunicationRecipient(str, Enum):
    CUSTOMER = "CUSTOMER"
    TECHNICIAN = "TECHNICIAN"
    DISPATCHER = "DISPATCHER"
    MANAGER = "MANAGER"
    SYSTEM = "SYSTEM"


CommunicationTone = Literal[
    "PROFESSIONAL",
    "FRIENDLY",
    "EMPATHETIC",
    "URGENT",
]


CustomerSentiment = Literal[
    "POSITIVE",
    "NEUTRAL",
    "NEGATIVE",
]


JobStatus = Literal[
    "CREATED",
    "ASSIGNED",
    "EN_ROUTE",
    "ON_SITE",
    "WORK_IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
]


# ==========================================================
# Communication Context
# ==========================================================


class CommunicationContext(BaseModel):
    """
    Validated information provided to the Communication Agent.

    This schema defines exactly what the Communication Agent
    is allowed to receive from the business-service layer.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    job_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description=(
            "FieldOps job identifier. It is sanitized before "
            "being sent to an external AI provider."
        ),
    )

    correlation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description=(
            "Correlation ID used to trace the complete "
            "communication workflow."
        ),
    )

    notification_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9_]+$",
        description=(
            "Notification/template event type, such as "
            "job_assigned or technician_en_route."
        ),
        examples=[
            "job_assigned",
            "technician_en_route",
        ],
    )

    recipient_type: CommunicationRecipient = Field(
        ...,
        description=(
            "Type of recipient receiving the communication."
        ),
    )

    channel: CommunicationChannel = Field(
        ...,
        description="Requested delivery channel.",
    )

    locale: str = Field(
        default="en",
        description=(
            "Requested locale, such as en or en-US."
        ),
    )

    @field_validator("locale", mode="before")
    @classmethod
    def normalize_request_locale(cls, v: Any) -> str:
        if not v or not str(v).strip():
            return "en"
        try:
            return normalize_locale(str(v))
        except InvalidLocaleError:
            raise ValueError("Invalid or unsupported locale.")

    customer_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
        description="Customer name when available.",
    )

    technician_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
        description="Assigned technician name when available.",
    )

    job_status: JobStatus = Field(
        ...,
        description="Current FieldOps job status.",
    )

    job_title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Customer-readable service or job title.",
    )

    eta: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description=(
            "Estimated arrival time supplied by the backend."
        ),
    )

    appointment_time: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description=(
            "Scheduled appointment time supplied by the backend."
        ),
    )

    sentiment: CustomerSentiment = Field(
        default="NEUTRAL",
        description="Current customer sentiment.",
    )

    additional_context: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
        description=(
            "Optional approved business context. "
            "This must not contain instructions that override "
            "system or business rules."
        ),
    )


# ==========================================================
# Communication Decision
# ==========================================================


class CommunicationDecision(BaseModel):
    """
    Structured content generated by the Communication Agent.

    Maximum channel lengths are deliberately not enforced in
    this schema.LengthValidator will perform those
    guardrail checks and trigger Jinja2 fallback when violated.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    channel: CommunicationChannel = Field(
        ...,
        description=(
            "Communication channel. It must match the requested "
            "channel in CommunicationContext."
        ),
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Required for PUSH. Optional for IN_APP. "
            "Not allowed for SMS or EMAIL."
        ),
    )

    subject: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Required for EMAIL. "
            "Not allowed for SMS, PUSH, or IN_APP."
        ),
    )

    message: str = Field(
        ...,
        min_length=1,
        description=(
            "Generated communication body or message."
        ),
    )

    tone: CommunicationTone = Field(
        ...,
        description="Tone used by the generated content.",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence score.",
    )

    # ------------------------------------------------------

    @model_validator(
        mode="after"
    )
    def validate_channel_fields(
        self,
    ) -> Self:
        """
        Enforce the output structure required by each channel.

        Length rules are not handled here. They belong to the
        LengthValidator so an oversized AI response
        can trigger an auditable Jinja2 fallback.
        """

        if self.channel == "EMAIL":
            if self.subject is None:
                raise ValueError(
                    "EMAIL communication requires subject."
                )

            if self.title is not None:
                raise ValueError(
                    "EMAIL communication must not include title."
                )

        elif self.channel == "SMS":
            if self.subject is not None:
                raise ValueError(
                    "SMS communication must not include subject."
                )

            if self.title is not None:
                raise ValueError(
                    "SMS communication must not include title."
                )

        elif self.channel == "PUSH":
            if self.title is None:
                raise ValueError(
                    "PUSH communication requires title."
                )

            if self.subject is not None:
                raise ValueError(
                    "PUSH communication must not include subject."
                )

        elif self.channel == "IN_APP":
            if self.subject is not None:
                raise ValueError(
                    "IN_APP communication must not include subject."
                )

        return self