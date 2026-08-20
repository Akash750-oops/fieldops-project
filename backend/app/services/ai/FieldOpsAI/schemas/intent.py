"""
intent.py

Pydantic schemas for the FieldOps Intent Recognition Engine.

The Intent Recognition Engine analyzes customer communication
and identifies the customer's primary intent.
"""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


# ==========================================================
# Message Intent
# ==========================================================


class MessageIntent(str, Enum):
    """
    Supported customer communication intents.
    """

    STATUS_INQUIRY = "STATUS_INQUIRY"
    COMPLAINT = "COMPLAINT"
    COMPLIMENT = "COMPLIMENT"
    CANCELLATION = "CANCELLATION"
    GENERAL_QUESTION = "GENERAL_QUESTION"
    ESCALATION_REQUEST = "ESCALATION_REQUEST"


# ==========================================================
# Intent Context
# ==========================================================


class IntentContext(BaseModel):
    """
    Input provided to the Intent Recognition Engine.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Customer communication to classify.",
    )

    language: str = Field(
        ...,
        min_length=2,
        max_length=10,
        description="Language of the customer communication.",
    )


# ==========================================================
# Intent Result
# ==========================================================


class IntentResult(BaseModel):
    """
    Structured result returned by the Intent Recognition Engine.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    intent: MessageIntent = Field(
        ...,
        description="Primary intent identified from the customer message.",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence score between 0.0 and 1.0.",
    )

    requires_human: bool = Field(
        ...,
        description=(
            "Whether human review is required. "
            "Messages with confidence below 0.7 require human review."
        ),
    )