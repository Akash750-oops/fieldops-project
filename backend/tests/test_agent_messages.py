"""
test_agent_messages.py

Unit tests for AI agent communication schemas.
"""

from __future__ import annotations

from app.services.ai.FieldOpsAI.schemas.agent_messages import (
    AgentAddress,
    CommandMessage,
    ErrorMessage,
    EventMessage,
    MessageType,
    QueryMessage,
    ResponseMessage,
)


# ==========================================================
# Agent Address
# ==========================================================


def test_agent_address_creation():
    """
    AgentAddress should be created successfully.
    """

    address = AgentAddress(
        agent_type="planning",
        agent_id="planner-01",
        tenant_id="tenant-001",
    )

    assert address.agent_type == "planning"

    assert address.agent_id == "planner-01"

    assert address.tenant_id == "tenant-001"

    assert (
        str(address)
        == "planning:planner-01:tenant-001"
    )


def test_agent_address_rejects_empty_fields():
    """
    Empty values should not be accepted.
    """

    try:

        AgentAddress(
            agent_type="",
            agent_id="planner",
            tenant_id="tenant",
        )

        assert False

    except ValueError:

        assert True


# ==========================================================
# Command Message
# ==========================================================


def test_command_message():
    """
    Command message should validate.
    """

    sender = AgentAddress(
        agent_type="planning",
        agent_id="planner-01",
        tenant_id="tenant-001",
    )

    recipient = AgentAddress(
        agent_type="dispatch",
        agent_id="dispatcher-01",
        tenant_id="tenant-001",
    )

    message = CommandMessage(
        sender=sender,
        recipient=recipient,
        payload={
            "job_id": "JOB-100",
            "technician": "TECH-101",
        },
    )

    assert (
        message.message_type
        == MessageType.COMMAND
    )


# ==========================================================
# Query Message
# ==========================================================


def test_query_message():

    sender = AgentAddress(
        agent_type="monitoring",
        agent_id="monitor-01",
        tenant_id="tenant-001",
    )

    recipient = AgentAddress(
        agent_type="planning",
        agent_id="planner-01",
        tenant_id="tenant-001",
    )

    message = QueryMessage(
        sender=sender,
        recipient=recipient,
        payload={
            "job_id": "JOB-22"
        },
    )

    assert (
        message.message_type
        == MessageType.QUERY
    )


# ==========================================================
# Event Message
# ==========================================================


def test_event_message():

    sender = AgentAddress(
        agent_type="dispatch",
        agent_id="dispatcher-01",
        tenant_id="tenant-001",
    )

    recipient = AgentAddress(
        agent_type="monitoring",
        agent_id="monitor-01",
        tenant_id="tenant-001",
    )

    message = EventMessage(
        sender=sender,
        recipient=recipient,
        payload={
            "status": "ACCEPTED"
        },
    )

    assert (
        message.message_type
        == MessageType.EVENT
    )


# ==========================================================
# Response Message
# ==========================================================


def test_response_message():

    sender = AgentAddress(
        agent_type="planning",
        agent_id="planner-01",
        tenant_id="tenant-001",
    )

    recipient = AgentAddress(
        agent_type="dispatch",
        agent_id="dispatcher-01",
        tenant_id="tenant-001",
    )

    message = ResponseMessage(
        sender=sender,
        recipient=recipient,
        payload={
            "recommended": "TECH-101"
        },
    )

    assert message.success is True


# ==========================================================
# Error Message
# ==========================================================


def test_error_message():

    sender = AgentAddress(
        agent_type="dispatch",
        agent_id="dispatcher-01",
        tenant_id="tenant-001",
    )

    recipient = AgentAddress(
        agent_type="planning",
        agent_id="planner-01",
        tenant_id="tenant-001",
    )

    message = ErrorMessage(
        sender=sender,
        recipient=recipient,
        error_code="TECH_NOT_FOUND",
        error_message="Technician unavailable",
    )

    assert message.success is False


# ==========================================================
# JSON Serialization
# ==========================================================


def test_json_serialization():

    sender = AgentAddress(
        agent_type="planning",
        agent_id="planner-01",
        tenant_id="tenant-001",
    )

    recipient = AgentAddress(
        agent_type="dispatch",
        agent_id="dispatcher-01",
        tenant_id="tenant-001",
    )

    message = CommandMessage(
        sender=sender,
        recipient=recipient,
        payload={
            "job_id": "JOB-500"
        },
    )

    json_data = message.to_json()

    assert "COMMAND" in json_data

    assert "JOB-500" in json_data


# ==========================================================
# Dictionary Serialization
# ==========================================================


def test_dict_serialization():

    sender = AgentAddress(
        agent_type="planning",
        agent_id="planner-01",
        tenant_id="tenant-001",
    )

    recipient = AgentAddress(
        agent_type="dispatch",
        agent_id="dispatcher-01",
        tenant_id="tenant-001",
    )

    message = CommandMessage(
        sender=sender,
        recipient=recipient,
        payload={
            "job_id": "JOB-999"
        },
    )

    data = message.to_dict()

    restored = CommandMessage.from_dict(data)

    assert (
        restored.payload["job_id"]
        == "JOB-999"
    )
    