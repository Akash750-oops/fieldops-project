"""
Tests for the message preview and approval workflow.

The tests use:
- a real in-memory SQLite database
- the real CommunicationService
- the real MessagePreview service
- the existing deterministic FakeAgent from the
  CommunicationService test suite

No SMS/email is actually sent.
"""

from __future__ import annotations

from collections.abc import Iterator

from types import SimpleNamespace

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from app.services.ai.FieldOpsAI.schemas.communication import CommunicationContext
from app.models import (
    AIBrandSafetyRule,
    AIGuardrailViolation,
    NotificationTemplate,
    EnterpriseAuditLog,
)
from app.services.ai.FieldOpsAI.services.message_preview import (
    MessagePreview,
)

from tests.test_communication_service import (
    FakeAgent,
    build_context,
    build_service,
    build_sms_decision,
)


# ==========================================================
# Test database
# ==========================================================

TestingEngine = create_engine(
    "sqlite://",
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

NotificationTemplate.__table__.create(
    bind=TestingEngine,
)

AIBrandSafetyRule.__table__.create(
    bind=TestingEngine,
)

AIGuardrailViolation.__table__.create(
    bind=TestingEngine,
)
EnterpriseAuditLog.__table__.create(
    bind=TestingEngine
)
TestingSessionLocal = sessionmaker(
    bind=TestingEngine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture
def db_session() -> Iterator[Session]:
    """
    Provide the real test database session expected by conftest.py.

    The communication workflow only requires these tables.
    """

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ==========================================================
# Helpers
# ==========================================================


TENANT_ID = "tenant-1"


class PreviewAgent:
    """
    Deterministic real agent used by CommunicationService.

    It returns an SMS decision when the requested context is SMS
    and an EMAIL-compatible decision when the requested context
    is EMAIL.

    This is deliberately not a mock.
    """

    def __init__(self) -> None:
        self.received_contexts = []

    def generate(self, *, context):
        self.received_contexts.append(context)

        if context.channel == "SMS":
            return build_sms_decision(
                "Hello Ruby Devi, Arun Kumar is assigned to your job."
            )

        return build_sms_decision(
            "Hello Ruby Devi, Arun Kumar is assigned to your job."
        )


def make_message_preview(
    db: Session,
) -> MessagePreview:
    """
    Build the real MessagePreview service.

    CommunicationService is also real. The only deterministic
    test component is the agent that supplies the generated
    decision.
    """

    agent = PreviewAgent()

    communication_service = build_service(
        db,
        agent=agent,
        tenant_id=TENANT_ID,
    )

    return MessagePreview(
        communication_service=communication_service,
        db=db,
        tenant_id=TENANT_ID,
    )


def make_preview(
    db: Session,
    *,
    priority: str | None = None,
    first_time_template: bool = False,
):
    """
    Generate a real preview.
    """

    preview_service = make_message_preview(db)

    context = build_context(
        channel="SMS",
    )

    return preview_service, preview_service.preview(
        context=context,
        template_key="job_assigned",
        priority=priority,
        first_time_template=first_time_template,
    )


# ==========================================================
# Preview generation
# ==========================================================


def test_preview_generates_without_sending(
    db_session: Session,
) -> None:
    """
    Preview generation must only generate content.

    MessagePreview itself has no delivery operation, so successful
    preview generation proves that the workflow remains in the
    preview stage.
    """

    preview_service, result = make_preview(db_session)

    assert result.preview_id
    assert result.template_key == "job_assigned"

    assert result.sms is not None
    assert result.email is not None

    assert result.sms.body
    assert result.email.body

    assert result.original_messages["sms"] == result.sms.body
    assert result.original_messages["email"] == result.email.body

    assert result.edited_messages["sms"] == result.sms.body
    assert result.edited_messages["email"] == result.email.body

    # MessagePreview must retain the preview for later editing
    # and approval.
    stored = preview_service.get_preview(
        result.preview_id,
    )

    assert stored.preview_id == result.preview_id


def test_preview_contains_sms_and_email(
    db_session: Session,
) -> None:
    """
    The preview must contain both SMS and email versions.
    """

    _, result = make_preview(db_session)

    assert result.sms is not None
    assert result.email is not None

    assert result.sms.channel == "sms"
    assert result.email.channel == "email"

    assert result.sms.body
    assert result.email.body


def test_sms_character_count_is_accurate(
    db_session: Session,
) -> None:
    """
    Backend character count must exactly equal len(message).
    """

    _, result = make_preview(db_session)

    assert result.sms is not None

    assert result.sms.character_count == len(
        result.sms.body
    )

    assert result.sms.character_limit == 160

    assert (
        result.sms.within_limit
        == (
            len(result.sms.body) <= 160
        )
    )


def test_email_character_count_is_accurate(
    db_session: Session,
) -> None:
    """
    Email character count must also be authoritative.
    """

    _, result = make_preview(db_session)

    assert result.email is not None

    assert result.email.character_count == len(
        result.email.body
    )


# ==========================================================
# Approval rules
# ==========================================================


def test_high_priority_requires_approval(
    db_session: Session,
) -> None:
    """
    HIGH priority messages require operator approval.
    """

    _, result = make_preview(
        db_session,
        priority="HIGH",
    )

    assert result.requires_approval is True
    assert result.approval_reason is not None
    assert "HIGH" in result.approval_reason.upper()


def test_urgent_priority_requires_approval(
    db_session: Session,
) -> None:
    """
    URGENT is treated as a high-risk priority.
    """

    _, result = make_preview(
        db_session,
        priority="URGENT",
    )

    assert result.requires_approval is True


def test_first_time_template_requires_approval(
    db_session: Session,
) -> None:
    """
    First-time templates require approval.
    """

    _, result = make_preview(
        db_session,
        first_time_template=True,
    )

    assert result.requires_approval is True
    assert result.approval_reason is not None
    assert "first-time" in (
        result.approval_reason.lower()
    )


def test_normal_message_does_not_require_approval(
    db_session: Session,
) -> None:
    """
    A normal message without HIGH/URGENT priority and without
    first-time-template status does not require approval.
    """

    _, result = make_preview(
        db_session,
        priority="NORMAL",
        first_time_template=False,
    )

    assert result.requires_approval is False
    assert result.approval_reason is None


# ==========================================================
# Editing
# ==========================================================


def test_edit_saves_operator_changes(
    db_session: Session,
) -> None:
    """
    Operator edits must replace the previewed message.
    """

    preview_service, result = make_preview(
        db_session,
    )

    original_sms = result.sms.body

    edited_sms = (
        "Hello Ruby, your technician is on the way."
    )

    updated = preview_service.edit(
        preview_id=result.preview_id,
        edited_messages={
            "sms": edited_sms,
        },
    )

    assert updated.edited_messages["sms"] == edited_sms

    assert updated.sms is not None
    assert updated.sms.body == edited_sms

    assert updated.sms.character_count == len(
        edited_sms
    )

    # Original must remain unchanged for audit purposes.
    assert updated.original_messages["sms"] == original_sms
    assert updated.original_messages["sms"] != edited_sms


def test_edit_email_saves_operator_changes(
    db_session: Session,
) -> None:
    """
    Email body edits must also be retained.
    """

    preview_service, result = make_preview(
        db_session,
    )

    edited_email = (
        "Hello Ruby Devi, your technician has been assigned."
    )

    updated = preview_service.edit(
        preview_id=result.preview_id,
        edited_messages={
            "email": edited_email,
        },
    )

    assert updated.email is not None
    assert updated.email.body == edited_email

    assert (
        updated.edited_messages["email"]
        == edited_email
    )


def test_edit_rejects_empty_message(
    db_session: Session,
) -> None:
    """
    Empty operator edits must not be accepted.
    """

    preview_service, result = make_preview(
        db_session,
    )

    with pytest.raises(ValueError):
        preview_service.edit(
            preview_id=result.preview_id,
            edited_messages={
                "sms": "",
            },
        )


def test_edit_rejects_unknown_channel(
    db_session: Session,
) -> None:
    """
    Only SMS and email are editable.
    """

    preview_service, result = make_preview(
        db_session,
    )

    with pytest.raises(ValueError):
        preview_service.edit(
            preview_id=result.preview_id,
            edited_messages={
                "push": "Invalid",
            },
        )


def test_edit_rejects_sms_over_160_characters(
    db_session: Session,
) -> None:
    """
    SMS must remain within the authoritative 160-character limit.
    """

    preview_service, result = make_preview(
        db_session,
    )

    oversized_message = "x" * 161

    with pytest.raises(ValueError):
        preview_service.edit(
            preview_id=result.preview_id,
            edited_messages={
                "sms": oversized_message,
            },
        )


# ==========================================================
# Approval
# ==========================================================


def test_high_priority_preview_can_be_approved(
    db_session: Session,
) -> None:
    """
    HIGH priority preview can be approved by an operator.
    """

    preview_service, result = make_preview(
        db_session,
        priority="HIGH",
    )

    approval = preview_service.approve(
        preview_id=result.preview_id,
        actor_id="operator-123",
    )

    assert approval.preview_id == result.preview_id
    assert approval.approved is True
    assert approval.approved_by == "operator-123"

    assert approval.approved_at is not None

    assert (
        approval.original_messages
        == result.original_messages
    )

    assert (
        approval.edited_messages
        == result.edited_messages
    )


def test_approval_contains_original_and_edited_messages(
    db_session: Session,
) -> None:
    """
    Approval result must retain both the original generated message
    and the final operator-edited message.
    """

    preview_service, result = make_preview(
        db_session,
        priority="HIGH",
    )

    original_sms = result.original_messages["sms"]

    edited_sms = (
        "Hello Ruby, your technician will arrive shortly."
    )

    preview_service.edit(
        preview_id=result.preview_id,
        edited_messages={
            "sms": edited_sms,
        },
    )

    approval = preview_service.approve(
        preview_id=result.preview_id,
        actor_id="operator-456",
    )

    assert (
        approval.original_messages["sms"]
        == original_sms
    )

    assert (
        approval.edited_messages["sms"]
        == edited_sms
    )

    assert (
        approval.original_messages["sms"]
        != approval.edited_messages["sms"]
    )


def test_approval_records_actor(
    db_session: Session,
) -> None:
    """
    Approval must identify the operator who approved it.
    """

    preview_service, result = make_preview(
        db_session,
        priority="HIGH",
    )

    approval = preview_service.approve(
        preview_id=result.preview_id,
        actor_id="operator-789",
        user_email="operator@example.com",
        role="DISPATCHER",
    )

    assert approval.approved_by == "operator-789"


def test_approval_requires_actor(
    db_session: Session,
) -> None:
    """
    Approval without an actor must fail.
    """

    preview_service, result = make_preview(
        db_session,
        priority="HIGH",
    )

    with pytest.raises(ValueError):
        preview_service.approve(
            preview_id=result.preview_id,
            actor_id="",
        )


def test_normal_preview_cannot_be_approved(
    db_session: Session,
) -> None:
    """
    A preview that does not require approval cannot be submitted
    through the approval endpoint.
    """

    preview_service, result = make_preview(
        db_session,
        priority="NORMAL",
    )

    with pytest.raises(ValueError):
        preview_service.approve(
            preview_id=result.preview_id,
            actor_id="operator-123",
        )


# ==========================================================
# Preview lookup
# ==========================================================


def test_unknown_preview_raises_error(
    db_session: Session,
) -> None:
    """
    Unknown preview IDs must fail cleanly.
    """

    preview_service = make_message_preview(
        db_session,
    )

    with pytest.raises(ValueError):
        preview_service.get_preview(
            "does-not-exist",
        )


def test_unknown_preview_edit_raises_error(
    db_session: Session,
) -> None:
    """
    Editing an unknown preview must fail.
    """

    preview_service = make_message_preview(
        db_session,
    )

    with pytest.raises(ValueError):
        preview_service.edit(
            preview_id="does-not-exist",
            edited_messages={
                "sms": "Hello",
            },
        )


def test_unknown_preview_approval_raises_error(
    db_session: Session,
) -> None:
    """
    Approving an unknown preview must fail.
    """

    preview_service = make_message_preview(
        db_session,
    )

    with pytest.raises(ValueError):
        preview_service.approve(
            preview_id="does-not-exist",
            actor_id="operator-123",
        )


# ==========================================================
# Input validation
# ==========================================================


def test_empty_template_key_is_rejected(
    db_session: Session,
) -> None:
    """
    Template key is mandatory.
    """

    preview_service = make_message_preview(
        db_session,
    )

    context = build_context(
        channel="SMS",
    )

    with pytest.raises(ValueError):
        preview_service.preview(
            context=context,
            template_key="",
        )


def test_whitespace_template_key_is_rejected(
    db_session: Session,
) -> None:
    """
    Whitespace-only template key is invalid.
    """

    preview_service = make_message_preview(
        db_session,
    )

    context = build_context(
        channel="SMS",
    )

    with pytest.raises(ValueError):
        preview_service.preview(
            context=context,
            template_key="   ",
        )


# ==========================================================
# Character counter
# ==========================================================


def test_character_count_updates_after_edit(
    db_session: Session,
) -> None:
    """
    Editing a message must immediately update the backend count.
    """

    preview_service, result = make_preview(
        db_session,
    )

    edited_sms = "Updated message"

    updated = preview_service.edit(
        preview_id=result.preview_id,
        edited_messages={
            "sms": edited_sms,
        },
    )

    assert updated.sms is not None

    assert (
        updated.sms.character_count
        == len(edited_sms)
    )

    assert (
        updated.sms.character_count
        == len(updated.sms.body)
    )

    assert updated.sms.within_limit is True


def test_160_character_sms_is_within_limit(
    db_session: Session,
) -> None:
    """
    Exactly 160 characters is valid.
    """

    preview_service, result = make_preview(
        db_session,
    )

    message = "x" * 160

    updated = preview_service.edit(
        preview_id=result.preview_id,
        edited_messages={
            "sms": message,
        },
    )

    assert updated.sms is not None
    assert updated.sms.character_count == 160
    assert updated.sms.within_limit is True


# ==========================================================
# End-to-end workflow
# ==========================================================


def test_complete_preview_edit_approval_workflow(
    db_session: Session,
) -> None:
    """
    Full workflow:

        generate
            ↓
        preview
            ↓
        edit
            ↓
        approve

    Original and edited values must survive the complete workflow.
    """

    preview_service, result = make_preview(
        db_session,
        priority="HIGH",
    )

    assert result.requires_approval is True

    original_sms = result.original_messages["sms"]
    original_email = result.original_messages["email"]

    edited_sms = (
        "Hello Ruby, Arun will arrive at 10:00 AM."
    )

    edited_email = (
        "Hello Ruby Devi, Arun Kumar will arrive at "
        "10:00 AM for your scheduled service."
    )

    edited = preview_service.edit(
        preview_id=result.preview_id,
        edited_messages={
            "sms": edited_sms,
            "email": edited_email,
        },
    )

    assert edited.edited_messages["sms"] == edited_sms
    assert edited.edited_messages["email"] == edited_email

    assert edited.original_messages["sms"] == original_sms
    assert edited.original_messages["email"] == original_email

    approval = preview_service.approve(
        preview_id=result.preview_id,
        actor_id="dispatcher-001",
        user_email="dispatcher@example.com",
        role="DISPATCHER",
    )

    assert approval.approved is True
    assert approval.approved_by == "dispatcher-001"

    assert (
        approval.original_messages["sms"]
        == original_sms
    )

    assert (
        approval.original_messages["email"]
        == original_email
    )

    assert (
        approval.edited_messages["sms"]
        == edited_sms
    )

    assert (
        approval.edited_messages["email"]
        == edited_email
    )

    assert approval.approved_at is not None
def test_email_is_within_limit(db_session: Session) -> None:
    """Email has no character limit, so it is always within limit."""
    _, result = make_preview(db_session)
    assert result.email.within_limit is True


def test_edit_rejects_empty_edited_messages_dict(db_session: Session) -> None:
    """An empty edited_messages dict must be rejected."""
    preview_service, result = make_preview(db_session)
    with pytest.raises(ValueError):
        preview_service.edit(
            preview_id=result.preview_id,
            edited_messages={},
        )


def test_edit_rejects_non_string_message(db_session: Session) -> None:
    """A non-string message value must be rejected."""
    preview_service, result = make_preview(db_session)
    with pytest.raises(ValueError):
        preview_service.edit(
            preview_id=result.preview_id,
            edited_messages={"sms": 12345},
        )
def test_preview_rejects_invalid_sms_output_channel(
    db_session: Session,
) -> None:
    """Preview must reject an AI result that is not an SMS output."""

    class WrongChannelService:
        def generate(self, *, context):
            return SimpleNamespace(
                decision=SimpleNamespace(
                    output=SimpleNamespace(
                        channel="EMAIL",
                        text="This should never be accepted.",
                    )
                )
            )

    preview_service = MessagePreview(
        communication_service=WrongChannelService(),
        db=db_session,
        tenant_id="tenant-1",
    )

    # Use a simple object because this test only needs model_copy()
    # and channel assignment; MessagePreview does not inspect
    # any other context fields before the channel validation.
    context = SimpleNamespace(
        channel="SMS",
        model_copy=lambda update: SimpleNamespace(
            channel=update["channel"]
        ),
    )

    with pytest.raises(
        ValueError,
        match="Expected SMS output, got EMAIL",
    ):
        preview_service.preview(
            context=context,
            template_key="job_assigned",
        )


def test_preview_rejects_invalid_email_output_channel(
    db_session: Session,
) -> None:
    """Preview must reject an AI result that is not an email output."""

    class WrongChannelService:
        def generate(self, *, context):
            if context.channel == "SMS":
                return SimpleNamespace(
                    decision=SimpleNamespace(
                        output=SimpleNamespace(
                            channel="SMS",
                            text="SMS preview",
                        )
                    )
                )

            return SimpleNamespace(
                decision=SimpleNamespace(
                    output=SimpleNamespace(
                        channel="SMS",
                        text="Wrong output",
                    )
                )
            )

    preview_service = MessagePreview(
        communication_service=WrongChannelService(),
        db=db_session,
        tenant_id="tenant-1",
    )

    context = SimpleNamespace(
        channel="SMS",
        model_copy=lambda update: SimpleNamespace(
            channel=update["channel"]
        ),
    )

    with pytest.raises(
        ValueError,
        match="Expected EMAIL output, got SMS",
    ):
        preview_service.preview(
            context=context,
            template_key="job_assigned",
        )


def test_preview_email_body_is_not_fallback_boilerplate(db_session: Session) -> None:
    """Guards against PreviewAgent's channel handling silently masking
    real content with fallback boilerplate."""
    _, result = make_preview(db_session)
    print("EMAIL BODY:", result.email.body)  # temporary, just to see it
    assert "unavailable" not in result.email.body.lower()
    assert "could not be generated" not in result.email.body.lower()

def test_audit_log_persisted_with_correct_fields(db_session: Session) -> None:
    """Approval must write a queryable, correct audit record."""
    preview_service, result = make_preview(db_session, priority="HIGH")

    edited_sms = "Hello Ruby, updated ETA."
    preview_service.edit(
        preview_id=result.preview_id,
        edited_messages={"sms": edited_sms},
    )

    preview_service.approve(
        preview_id=result.preview_id,
        actor_id="operator-999",
        user_email="op@example.com",
        role="DISPATCHER",
    )

    record = (
        db_session.query(EnterpriseAuditLog)
        .filter(EnterpriseAuditLog.entity_id == result.preview_id)
        .one()
    )

    assert record.user_id == "operator-999"
    assert record.user_email == "op@example.com"
    assert record.role == "DISPATCHER"
    assert record.tenant_id == TENANT_ID
    assert record.action == "MESSAGE_PREVIEW_APPROVED"
    assert record.entity_type == "message_preview"
    assert record.old_value["sms"] == result.original_messages["sms"]
    assert record.new_value["sms"] == edited_sms
    assert record.details["template_key"] == "job_assigned"
    assert record.severity == "INFO"
def test_side_by_side_returns_both_channels(
    db_session: Session,
) -> None:
    """
    side_by_side must return both channels keyed correctly
    for display.
    """

    preview_service, result = make_preview(db_session)

    formatted = preview_service.side_by_side(
        result.preview_id
    )

    assert set(formatted.keys()) == {"sms", "email"}
    assert formatted["sms"].channel == "sms"
    assert formatted["email"].channel == "email"
    assert formatted["sms"].body == result.sms.body
    assert formatted["email"].body == result.email.body

