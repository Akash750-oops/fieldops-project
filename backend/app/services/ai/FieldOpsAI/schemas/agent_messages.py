"""
agent_messages.py

Standard message contracts for communication between AI agents.

Purpose
-------
This module defines the formal communication protocol used by
FieldOps Commander AI agents.

Every inter-agent communication must be wrapped inside a
MessageEnvelope and validated using Pydantic before processing.

Goals
-----
- Type-safe messaging
- Standardized communication
- JSON serialization
- Schema validation
- Versioned contracts
- Future compatibility

These schemas are transport-agnostic and may be used with:

- Redis Pub/Sub
- Celery
- Kafka
- RabbitMQ
- HTTP
- gRPC
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================================
# Message Types
# ==========================================================


class MessageType(str, Enum):
    """
    Supported AI message types.
    """

    COMMAND = "COMMAND"

    QUERY = "QUERY"

    EVENT = "EVENT"

    RESPONSE = "RESPONSE"

    ERROR = "ERROR"


# ==========================================================
# Agent Address
# ==========================================================


class AgentAddress(BaseModel):
    """
    Unique address of an AI agent.

    Format
    ------
    agent_type:agent_id:tenant_id

    Example
    -------
    planning:planner-01:tenant-001
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    agent_type: str = Field(
        ...,
        description="Agent type (planning, dispatch, monitoring, etc.)",
        examples=["planning"],
    )

    agent_id: str = Field(
        ...,
        description="Unique agent identifier.",
        examples=["planner-01"],
    )

    tenant_id: str = Field(
        ...,
        description="Tenant identifier.",
        examples=["tenant-001"],
    )

    @field_validator(
        "agent_type",
        "agent_id",
        "tenant_id",
    )
    @classmethod
    def validate_not_empty(
        cls,
        value: str,
    ) -> str:
        """
        Ensure address fields are not empty.
        """

        value = value.strip()

        if not value:
            raise ValueError(
                "Address fields cannot be empty."
            )

        if ":" in value:
            raise ValueError(
                "Address fields cannot contain ':'."
            )

        return value

    @property
    def address(self) -> str:
        """
        Return the canonical address string.
        """

        return (
            f"{self.agent_type}:"
            f"{self.agent_id}:"
            f"{self.tenant_id}"
        )

    def __str__(self) -> str:
        return self.address


# ==========================================================
# Message Envelope
# ==========================================================


class MessageEnvelope(BaseModel):
    """
    Standard envelope that wraps every AI message.

    Every communication between AI agents must include:

    - Sender
    - Recipient
    - Message Type
    - Payload
    - Timestamp
    - Correlation ID
    - Contract Version
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    sender: AgentAddress = Field(
        ...,
        description="Originating AI agent.",
    )

    recipient: AgentAddress = Field(
        ...,
        description="Destination AI agent.",
    )

    message_type: MessageType = Field(
        ...,
        description="Communication type.",
    )

    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Message payload.",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the message was created.",
    )

    correlation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier used to correlate requests and responses.",
    )

    contract_version: str = Field(
        default="1.0",
        description="Communication contract version.",
    )

    timeout_seconds: float | None = Field(
    default=None,
    gt=0,
    description=(
        "Optional timeout in seconds. "
        "Fractional values such as 0.5 are supported."
    ),
    examples=[5.0],
)


# ==========================================================
# Base Message
# ==========================================================


class BaseMessage(MessageEnvelope):
    """
    Base class for every AI message.

    Specialized message types inherit from this class.

    This avoids duplication while ensuring all
    communications follow the same contract.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    def to_json(self) -> str:
        """
        Serialize the message into JSON.
        """

        return self.model_dump_json(
            indent=2,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the message into a dictionary.
        """

        return self.model_dump()

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "BaseMessage":
        """
        Deserialize a dictionary into a message.
        """

        return cls.model_validate(data)
# ==========================================================
# Command Message
# ==========================================================


class CommandMessage(BaseMessage):
    """
    Command sent from one AI agent to another.

    Commands instruct another agent to perform an action.

    Example
    -------
    Planning Agent
            ↓
    Dispatch Agent

    "Assign technician TECH-101"
    """

    message_type: MessageType = Field(
        default=MessageType.COMMAND,
        frozen=True,
    )


# ==========================================================
# Query Message
# ==========================================================


class QueryMessage(BaseMessage):
    """
    Query sent when an agent needs information.

    Example
    -------
    Monitoring Agent
            ↓
    Planning Agent

    "Who is the nearest technician?"
    """

    message_type: MessageType = Field(
        default=MessageType.QUERY,
        frozen=True,
    )


# ==========================================================
# Event Message
# ==========================================================


class EventMessage(BaseMessage):
    """
    Event broadcast between AI agents.

    Events announce that something happened.

    Example
    -------
    Dispatch Agent
            ↓
    Monitoring Agent

    Technician accepted job.
    """

    message_type: MessageType = Field(
        default=MessageType.EVENT,
        frozen=True,
    )


# ==========================================================
# Response Message
# ==========================================================


class ResponseMessage(BaseMessage):
    """
    Successful response returned after a
    command or query.

    Example
    -------
    Planning Agent

    Recommended Technician:
    TECH-101
    """

    message_type: MessageType = Field(
        default=MessageType.RESPONSE,
        frozen=True,
    )

    success: bool = Field(
        default=True,
        description="Indicates successful execution.",
    )


# ==========================================================
# Error Message
# ==========================================================


class ErrorMessage(BaseMessage):
    """
    Error returned when an AI request fails.

    Example
    -------
    Dispatch Agent

    Technician unavailable.
    """

    message_type: MessageType = Field(
        default=MessageType.ERROR,
        frozen=True,
    )

    success: bool = Field(
        default=False,
        description="Indicates failed execution.",
    )

    error_code: str = Field(
        ...,
        description="Machine-readable error code.",
        examples=["TECHNICIAN_NOT_AVAILABLE"],
    )

    error_message: str = Field(
        ...,
        description="Human-readable error message.",
    )

    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional error details.",
    )