"""
Tests for the approved Jinja2 guardrail fallback service.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from app.models import NotificationTemplate
from app.services.ai.FieldOpsAI.schemas.communication import (
    CommunicationContext,
)
from app.services.ai.guardrails.fallback_service import (
    FallbackTemplateSource,
    GuardrailFallbackService,
)
from app.services.ai.guardrails.pipeline import (
    GuardrailPipeline,
)


# ==========================================================
# Database Fixture
# ==========================================================


@pytest.fixture
def db_session() -> Iterator[Session]:
    """
    Create an isolated template database.
    """

    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    NotificationTemplate.__table__.create(
        bind=engine
    )

    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    session = testing_session()

    try:
        yield session

    finally:
        session.close()

        NotificationTemplate.__table__.drop(
            bind=engine
        )

        engine.dispose()


# ==========================================================
# Test Helpers
# ==========================================================


def build_context(
    *,
    channel: str = "SMS",
    locale: str = "en",
    notification_type: str = "job_assigned",
    customer_name: str | None = (
        "{{customer_name}}"
    ),
    technician_name: str | None = (
        "{{technician_name}}"
    ),
) -> CommunicationContext:
    """
    Build a sanitized communication context.
    """

    return CommunicationContext(
        job_id="{{job_id}}",
        correlation_id="correlation-1",
        notification_type=notification_type,
        recipient_type="CUSTOMER",
        channel=channel,
        locale=locale,
        customer_name=customer_name,
        technician_name=technician_name,
        job_status="ASSIGNED",
        job_title="{{job_title}}",
        eta="{{eta}}",
        sentiment="NEUTRAL",
    )


def add_template(
    db: Session,
    *,
    channel: str,
    locale: str = "en",
    title_template: str | None = (
        "FieldOps update"
    ),
    body_template: str = (
        "Hello {{customer_name}}."
    ),
    notification_type: str = (
        "job_assigned"
    ),
    version: int = 1,
) -> NotificationTemplate:
    """
    Insert one active notification template.
    """

    row = NotificationTemplate(
        name="Test fallback",
        type=notification_type,
        channel=channel,
        locale=locale,
        format=(
            "html"
            if channel == "email"
            else "text"
        ),
        title_template=title_template,
        body_template=body_template,
        version=version,
        is_active=True,
    )

    db.add(
        row
    )

    db.commit()

    db.refresh(
        row
    )

    return row


# ==========================================================
# Database Rendering Tests
# ==========================================================


def test_sms_uses_active_database_template(
    db_session: Session,
) -> None:
    """
    SMS fallback uses the active database template.
    """

    row = add_template(
        db_session,
        channel="sms",
        title_template=None,
        body_template=(
            "Hello {{customer_name}}, "
            "{{technician_name}} is assigned."
        ),
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context()
    )

    assert (
        result.source
        == FallbackTemplateSource.DATABASE
    )

    assert result.template_id == row.id
    assert result.template_version == 1

    assert result.decision.channel == "SMS"
    assert result.decision.title is None
    assert result.decision.subject is None

    assert result.decision.message == (
        "Hello {{customer_name}}, "
        "{{technician_name}} is assigned."
    )


def test_email_maps_title_to_subject(
    db_session: Session,
) -> None:
    """
    Email template titles become email subjects.
    """

    add_template(
        db_session,
        channel="email",
        title_template="Job assigned",
        body_template=(
            "<p>Hello {{customer_name}}</p>"
        ),
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context(
            channel="EMAIL"
        )
    )

    assert result.decision.channel == "EMAIL"

    assert (
        result.decision.subject
        == "Job assigned"
    )

    assert result.decision.title is None

    assert (
        "{{customer_name}}"
        in result.decision.message
    )


def test_push_maps_title_correctly(
    db_session: Session,
) -> None:
    """
    Push template title becomes the push title.
    """

    add_template(
        db_session,
        channel="push",
        title_template="Technician assigned",
        body_template="ETA {{eta}}",
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context(
            channel="PUSH"
        )
    )

    assert result.decision.channel == "PUSH"

    assert result.decision.title == (
        "Technician assigned"
    )

    assert result.decision.subject is None

    assert result.decision.message == (
        "ETA {{eta}}"
    )


def test_in_app_supports_optional_title(
    db_session: Session,
) -> None:
    """
    In-app communication may omit its title.
    """

    add_template(
        db_session,
        channel="in_app",
        title_template=None,
        body_template=(
            "Your request was updated."
        ),
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context(
            channel="IN_APP"
        )
    )

    assert result.decision.channel == "IN_APP"
    assert result.decision.title is None
    assert result.decision.subject is None


# ==========================================================
# Locale Tests
# ==========================================================


def test_requested_locale_falls_back_to_base_language(
    db_session: Session,
) -> None:
    """
    en-US may use an approved en template.
    """

    add_template(
        db_session,
        channel="sms",
        locale="en",
        title_template=None,
        body_template="Service update.",
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context(
            locale="en-US"
        )
    )

    assert (
        result.source
        == FallbackTemplateSource.DATABASE
    )

    assert result.requested_locale == "en-US"
    assert result.resolved_locale == "en"


# ==========================================================
# Template Version Test
# ==========================================================


def test_latest_active_database_version_is_selected(
    db_session: Session,
) -> None:
    """
    The newest active template is selected.
    """

    add_template(
        db_session,
        channel="sms",
        title_template=None,
        body_template="Older template.",
        version=1,
    )

    latest = add_template(
        db_session,
        channel="sms",
        title_template=None,
        body_template="Latest template.",
        version=2,
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context()
    )

    assert result.template_id == latest.id
    assert result.template_version == 2

    assert result.decision.message == (
        "Latest template."
    )


# ==========================================================
# Built-in and Emergency Tests
# ==========================================================


def test_missing_database_template_uses_builtin(
    db_session: Session,
) -> None:
    """
    Built-in defaults are used when no DB template exists.
    """

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context()
    )

    assert (
        result.source
        == FallbackTemplateSource.BUILTIN
    )

    assert result.decision.channel == "SMS"

    assert (
        "{{customer_name}}"
        in result.decision.message
    )


def test_unknown_notification_type_uses_emergency(
    db_session: Session,
) -> None:
    """
    Unknown event types receive a generic safe fallback.
    """

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context(
            notification_type="unknown_event"
        )
    )

    assert (
        result.source
        == FallbackTemplateSource.EMERGENCY
    )

    assert result.decision.message == (
        "Your FieldOps service request has an update. "
        "Please check the app."
    )


# ==========================================================
# Invalid Template Tests
# ==========================================================


def test_unsupported_database_variable_is_not_rendered(
    db_session: Session,
) -> None:
    """
    Unknown variables force the service to use a safer
    template.
    """

    add_template(
        db_session,
        channel="sms",
        title_template=None,
        body_template="Secret: {{api_key}}",
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context()
    )

    assert (
        result.source
        == FallbackTemplateSource.BUILTIN
    )

    assert (
        "api_key"
        not in result.decision.message
    )


def test_broken_database_template_uses_builtin(
    db_session: Session,
) -> None:
    """
    Invalid Jinja syntax does not break fallback delivery.
    """

    add_template(
        db_session,
        channel="sms",
        title_template=None,
        body_template=(
            "{% if customer_name %}"
        ),
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context()
    )

    assert (
        result.source
        == FallbackTemplateSource.BUILTIN
    )


def test_oversized_sms_database_template_uses_builtin(
    db_session: Session,
) -> None:
    """
    An oversized database SMS is rejected.
    """

    add_template(
        db_session,
        channel="sms",
        title_template=None,
        body_template="x" * 161,
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=build_context()
    )

    assert (
        result.source
        == FallbackTemplateSource.BUILTIN
    )

    assert (
        len(
            result.decision.message
        )
        <= 160
    )


# ==========================================================
# Optional Value Tests
# ==========================================================


def test_missing_optional_values_never_render_none_or_null(
    db_session: Session,
) -> None:
    """
    Missing optional values use safe generic wording.
    """

    add_template(
        db_session,
        channel="sms",
        title_template=None,
        body_template=(
            "Hello {{customer_name}}, "
            "{{technician_name}} is assigned."
        ),
    )

    context = build_context(
        customer_name=None,
        technician_name=None,
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=context
    )

    lowered = (
        result.decision.message.lower()
    )

    assert "none" not in lowered
    assert "null" not in lowered

    assert result.decision.message == (
        "Hello Customer, "
        "Your technician is assigned."
    )


# ==========================================================
# Context Safety Test
# ==========================================================


def test_free_form_additional_context_is_not_available_to_template(
    db_session: Session,
) -> None:
    """
    Free-form context cannot be copied directly by a template.
    """

    add_template(
        db_session,
        channel="sms",
        title_template=None,
        body_template=(
            "{{additional_context}}"
        ),
    )

    context = build_context().model_copy(
        update={
            "additional_context": (
                "private free-form data"
            ),
        }
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=context
    )

    assert (
        result.source
        == FallbackTemplateSource.BUILTIN
    )

    assert (
        "private free-form data"
        not in result.decision.message
    )


# ==========================================================
# HTML Safety Test
# ==========================================================


def test_database_email_variables_are_html_escaped(
    db_session: Session,
) -> None:
    """
    Dynamic email values are escaped before HTML output.
    """

    add_template(
        db_session,
        channel="email",
        title_template="Service update",
        body_template=(
            "<p>Hello {{customer_name}}</p>"
        ),
    )

    context = build_context(
        channel="EMAIL",
        customer_name=(
            "<script>alert(1)</script>"
        ),
    )

    result = GuardrailFallbackService(
        db=db_session
    ).render(
        context=context
    )

    assert (
        "<script>"
        not in result.decision.message
    )

    assert (
        "&lt;script&gt;"
        in result.decision.message
    )


# ==========================================================
# Guardrail Compatibility Test
# ==========================================================


def test_rendered_fallback_passes_default_guardrails(
    db_session: Session,
) -> None:
    """
    Approved fallback output passes the local guardrails.
    """

    context = build_context()

    fallback = GuardrailFallbackService(
        db=db_session
    ).render(
        context=context
    )

    guardrail_result = (
        GuardrailPipeline.default().run(
            context=context,
            decision=fallback.decision,
        )
    )

    assert guardrail_result.passed is True


from app.services.ai.guardrails.fallback_service import GuardrailFallbackService
from app.services.ai.FieldOpsAI.schemas.communication import CommunicationContext

def test_database_lookup_failure_reaches_builtin_fallback(db_session, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    def mock_query(*args, **kwargs):
        raise SQLAlchemyError("DB Down")
    monkeypatch.setattr(db_session, "query", mock_query)
    
    svc = GuardrailFallbackService(db=db_session)
    ctx = CommunicationContext(job_id="1", notification_type="job_assigned", recipient_type="CUSTOMER", channel="SMS", locale="es", job_status="ASSIGNED")
    res = svc.render(context=ctx)
    assert res.source == "BUILTIN"

def test_spanish_missing_optional_values_use_spanish_defaults(db_session):
    svc = GuardrailFallbackService(db=db_session)
    ctx = CommunicationContext(job_id="1", notification_type="job_assigned", recipient_type="CUSTOMER", channel="SMS", locale="es", job_status="ASSIGNED")
    res = svc.render(context=ctx)
    assert "Cliente" in res.decision.message or "técnico" in res.decision.message

def test_tamil_missing_optional_values_use_tamil_defaults(db_session):
    svc = GuardrailFallbackService(db=db_session)
    ctx = CommunicationContext(job_id="1", notification_type="job_assigned", recipient_type="CUSTOMER", channel="SMS", locale="ta", job_status="ASSIGNED")
    res = svc.render(context=ctx)
    assert "வாடிக்கையாளர்" in res.decision.message or "தொழில்நுட்பவியலாளர்" in res.decision.message

def test_hindi_missing_optional_values_use_hindi_defaults(db_session):
    svc = GuardrailFallbackService(db=db_session)
    ctx = CommunicationContext(job_id="1", notification_type="job_assigned", recipient_type="CUSTOMER", channel="SMS", locale="hi", job_status="ASSIGNED")
    res = svc.render(context=ctx)
    assert "ग्राहक" in res.decision.message or "तकनीशियन" in res.decision.message
