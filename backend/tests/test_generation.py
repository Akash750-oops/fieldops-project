from __future__ import annotations
import os
from dotenv import load_dotenv


import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Module under test — adjust this import if AIMessageGenerator lives
# somewhere else in your tree.
# ---------------------------------------------------------------------------
MODULE_PATH = "app.services.ai.FieldOpsAI.generators.ai_generator"

from app.services.ai.FieldOpsAI.generators import AIMessageGenerator  # noqa: E402
from app.services.ai.FieldOpsAI.schemas.communication import (  # noqa: E402
    CommunicationContext,
    CommunicationRecipient,
)
from app.services.ai.guardrails.fallback_service import (  # noqa: E402
    GuardrailFallbackResult,
)

# REAL pii_sanitizer — full source was available, so we exercise the
# genuine sanitize -> sanitize_prompt -> restore_data round trip instead
# of mocking it. This is the single most safety-critical piece of the
# pipeline (nothing unsanitized may reach Groq), so it deserves real
# coverage rather than a stub.
from app.services.ai.pii_sanitizer import pii_sanitizer as real_pii_sanitizer  # noqa: E402

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATUSES = ["created", "assigned", "enroute", "onsite", "completed", "cancelled"]
CHANNELS = ["SMS", "EMAIL", "PUSH"]
PATHS = ["ai", "fallback"]

# Friendly test-id status -> real JobStatus Literal value from the schema.
STATUS_TO_JOBSTATUS = {
    "created": "CREATED",
    "assigned": "ASSIGNED",
    "enroute": "EN_ROUTE",
    "onsite": "ON_SITE",
    "completed": "COMPLETED",
    "cancelled": "CANCELLED",
}

AI_LATENCY_BUDGET_SECONDS = 5.0
FALLBACK_LATENCY_BUDGET_SECONDS = 0.050  # 50 ms

# Realistic per-status job fixtures (6 jobs), trimmed to fields that
# actually exist on the real CommunicationContext schema (extra="forbid"
# means anything else raises ValidationError at construction time).
JOB_FIXTURES = {
    "created": {
        "job_id": "JOB-CREATED-001",
        "notification_type": "job_created",
        "recipient_type": CommunicationRecipient.CUSTOMER,
        "customer_name": "Ravi Kumar",
        "technician_name": None,
        "job_title": "AC installation",
        "locale": "en",
    },
    "assigned": {
        "job_id": "JOB-ASSIGNED-002",
        "notification_type": "job_assigned",
        "recipient_type": CommunicationRecipient.CUSTOMER,
        "customer_name": "Anita Sharma",
        "technician_name": "Suresh Babu",
        "job_title": "Plumbing repair",
        "locale": "en",
    },
    "enroute": {
        "job_id": "JOB-ENROUTE-003",
        "notification_type": "technician_en_route",
        "recipient_type": CommunicationRecipient.CUSTOMER,
        "customer_name": "Karthik Iyer",
        "technician_name": "Ramesh Pillai",
        "job_title": "Electrical inspection",
        "eta": "15 minutes",
        "locale": "en",
    },
    "onsite": {
        "job_id": "JOB-ONSITE-004",
        "notification_type": "technician_on_site",
        "recipient_type": CommunicationRecipient.CUSTOMER,
        "customer_name": "Divya Menon",
        "technician_name": "Suresh Babu",
        "job_title": "Appliance repair",
        "appointment_time": "10:45 AM",
        "locale": "en",
    },
    "completed": {
        "job_id": "JOB-COMPLETED-005",
        "notification_type": "job_completed",
        "recipient_type": CommunicationRecipient.CUSTOMER,
        "customer_name": "Mohammed Faizal",
        "technician_name": "Ramesh Pillai",
        "job_title": "Water heater service",
        "locale": "en",
    },
    "cancelled": {
        "job_id": "JOB-CANCELLED-006",
        "notification_type": "job_cancelled",
        "recipient_type": CommunicationRecipient.CUSTOMER,
        "customer_name": "Lakshmi Narayanan",
        "technician_name": None,
        "job_title": "HVAC maintenance",
        "locale": "en",
    },
}

# Channel-appropriate sample AI output bodies used to configure the mocked
# GroqClient response for a given test. These use the REAL placeholder
# syntax the actual pii_sanitizer produces ({{customer_name}}, {{job_id}}),
# simulating what a real LLM would echo back after receiving a sanitized
# prompt — so restore_data() has something genuine to restore.
SAMPLE_AI_BODY = {
    "SMS": "Hi {{customer_name}}, your job {{job_id}} is now {status}. - FieldOps",
    "EMAIL": (
        "<html><body><h1>Job Update</h1>"
        "<p>Dear {{customer_name}}, your job <b>{{job_id}}</b> is now "
        "<strong>{status}</strong>.</p></body></html>"
    ),
    "PUSH": "Hi {{customer_name}}, Job {{job_id}}: {status}",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _build_context(status: str, channel: str) -> CommunicationContext:
    """
    Build a REAL CommunicationContext instance.

    schemas/communication.py is now available, so we construct a genuine
    pydantic instance instead of a MagicMock(spec=...). This means
    real_pii_sanitizer.sanitize()'s call to context.model_dump(mode="python")
    exercises actual pydantic serialization, and schema-level validation
    (field lengths, notification_type pattern, job_status Literal, etc.)
    is genuinely enforced rather than assumed away.
    """
    data = dict(JOB_FIXTURES[status])
    data["channel"] = channel
    data["job_status"] = STATUS_TO_JOBSTATUS[status]
    return CommunicationContext(**data)


@pytest.fixture
def budget_manager():
    mgr = MagicMock()
    mgr.check.return_value = SimpleNamespace(allowed=True)
    return mgr


# ---------------------------------------------------------------------------
# In-memory SQLite database — defined here only (no separate conftest.py),
# so this file is fully self-contained.
#
# Adjust BASE_IMPORT_PATH to wherever your project's SQLAlchemy declarative
# Base actually lives (e.g. "app.db.base", "app.models.base") so real
# tables get created in SQLite. Until then, this still hands back a
# genuine SQLAlchemy Session with an empty schema, which is enough for any
# test that mocks the DB-backed services themselves (as this suite
# currently does for GuardrailFallbackService) and is ready to go the
# moment real DB-backed template tests are added.
# ---------------------------------------------------------------------------

BASE_IMPORT_PATH = "app.db.base"


def _try_import_base():
    try:
        module_path, attr = BASE_IMPORT_PATH.rsplit(".", 1)
        module = __import__(module_path, fromlist=[attr])
        return getattr(module, attr)
    except Exception:
        return None


@pytest.fixture(scope="function")
def sqlite_engine():
    """Fresh in-memory SQLite engine per test — fast, isolated."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    base = _try_import_base()
    if base is not None:
        base.metadata.create_all(bind=engine)

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def sqlite_session(sqlite_engine):
    """
    Real SQLAlchemy Session backed by the in-memory SQLite engine. Use
    this instead of MagicMock(spec=Session) wherever a test needs to
    exercise actual DB-backed code paths rather than just asserting mock
    calls.
    """
    SessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def db_session(sqlite_session):
    """
    Real SQLite-backed Session, used wherever AIMessageGenerator /
    GuardrailFallbackService need a `db: Session`. GuardrailFallbackService
    itself is still mocked below (its internals depend on template_engine
    / default_template / prompt_locale_service, none of which have been
    shared yet), so this session isn't exercised for real DB reads yet —
    but it's a genuine Session object rather than a MagicMock, so it's
    ready the moment those pieces are wired in.
    """
    return sqlite_session


@pytest.fixture
def patched_dependencies(monkeypatch):
    """
    Replace external dependencies AIMessageGenerator talks to with mocks,
    so __init__ never opens a real Redis/Groq connection or needs
    template_engine internals we don't have yet.

    pii_sanitizer is deliberately NOT mocked here — the real singleton is
    used (see real_pii_sanitizer import above), so sanitize/restore
    behavior is genuinely tested.

    CommunicationDecision and MessageOutputFormatter are still mocked —
    see ASSUMPTIONS #3 above for why.
    """
    fake_groq_cls = MagicMock()
    fake_fallback_cls = MagicMock()
    fake_pipeline_cls = MagicMock()
    fake_pipeline_cls.default.return_value = MagicMock()

    monkeypatch.setattr(f"{MODULE_PATH}.GroqClient", fake_groq_cls)
    monkeypatch.setattr(f"{MODULE_PATH}.GuardrailFallbackService", fake_fallback_cls)
    monkeypatch.setattr(f"{MODULE_PATH}.GuardrailPipeline", fake_pipeline_cls)

    fake_formatter = MagicMock()
    # Default passthrough formatting; individual tests override return_value.
    fake_formatter.format.side_effect = (
        lambda channel, rendered_title, rendered_body, template_format: rendered_body
    )
    monkeypatch.setattr(f"{MODULE_PATH}.MessageOutputFormatter", fake_formatter)

    fake_decision_cls = MagicMock()
    fake_decision_cls.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
    monkeypatch.setattr(f"{MODULE_PATH}.CommunicationDecision", fake_decision_cls)

    return SimpleNamespace(
        groq_cls=fake_groq_cls,
        fallback_cls=fake_fallback_cls,
        pipeline_cls=fake_pipeline_cls,
        formatter=fake_formatter,
        decision_cls=fake_decision_cls,
    )


@pytest.fixture(autouse=True)
def clean_pii_state():
    """
    The real pii_sanitizer is a stateless singleton (per its own
    docstring), but each PlaceholderMap it hands back is request-scoped.
    Nothing to reset globally — this fixture exists as an explicit,
    documented no-op so it's obvious the suite considered this and it's
    safe to run tests in parallel/any order.
    """
    yield


@pytest.fixture
def generator(db_session, budget_manager, patched_dependencies):
    gen = AIMessageGenerator(db=db_session, budget_manager=budget_manager)
    # __init__ constructed these from the patched classes; grab handles so
    # each test can configure .return_value / .side_effect directly.
    return gen


def _configure_ai_success(generator, status: str, channel: str):
    """
    Wire the mocked GroqClient + guardrails to a clean success path.

    The "AI response" body deliberately echoes back the REAL placeholder
    tokens ({{customer_name}}, {{job_id}}) that pii_sanitizer.sanitize()
    would have produced for this fixture's data — simulating a real LLM
    that only ever saw sanitized input. This lets us assert that
    restore_data() genuinely restores the original values afterward.
    """
    body = SAMPLE_AI_BODY[channel].replace("{status}", status)
    generator.groq_client.generate_result.return_value = SimpleNamespace(text=body)
    generator.guardrail_pipeline.run.return_value = SimpleNamespace(passed=True)
    return body


def _configure_forced_fallback(generator, reason: str = "guardrail"):
    """
    Force message_generate down the fallback path via the given reason,
    and wire fallback_service.render to a deterministic result.
    """
    fallback_result = GuardrailFallbackResult(
        message="Fallback template message",
        template_source="built_in",
    ) if _fallback_result_is_constructible() else MagicMock(
        message="Fallback template message", template_source="built_in"
    )
    generator.fallback_service.render.return_value = fallback_result

    if reason == "guardrail":
        generator.groq_client.generate_result.return_value = SimpleNamespace(
            text="AI generated but unsafe"
        )
        generator.guardrail_pipeline.run.return_value = SimpleNamespace(passed=False)
    elif reason == "groq_error":
        generator.groq_client.generate_result.side_effect = RuntimeError("Groq down")
    elif reason == "empty_response":
        generator.groq_client.generate_result.return_value = SimpleNamespace(text="   ")
    return fallback_result


def _fallback_result_is_constructible() -> bool:
    """
    GuardrailFallbackResult's real constructor signature is unknown to this
    suite; try it, and fall back to a MagicMock stand-in if it needs fields
    we don't have. Keeps the suite runnable without the real schema.
    """
    try:
        GuardrailFallbackResult(message="x", template_source="built_in")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# SECTION 1 — 72 CORE TESTS
# 6 statuses x 3 channels x 2 paths x 2 assertion passes = 72
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", STATUSES)
@pytest.mark.parametrize("channel", CHANNELS)
@pytest.mark.parametrize("path", PATHS)
async def test_core_content_correctness(generator, status, channel, path):
    """
    Pass (a): verifies message_generate returns the *right kind* of result
    for the given path, with PII correctly restored / templated, for every
    status x channel combination.
    """
    ctx = _build_context(status, channel)

    if path == "ai":
        _configure_ai_success(generator, status, channel)
        result = await generator.message_generate(
            context=ctx, template_key=f"{status}_{channel.lower()}", channel=channel
        )
        text = result if isinstance(result, str) else getattr(result, "output", str(result))
        assert "{{" not in text and "}}" not in text, (
            "Real pii_sanitizer placeholder tokens must be fully restored"
        )
        assert JOB_FIXTURES[status]["customer_name"] in text
        assert JOB_FIXTURES[status]["job_id"] in text
    else:
        fallback_result = _configure_forced_fallback(generator, reason="guardrail")
        result = await generator.message_generate(
            context=ctx, template_key=f"{status}_{channel.lower()}", channel=channel
        )
        assert result is fallback_result
        generator.fallback_service.render.assert_called_once()


@pytest.mark.parametrize("status", STATUSES)
@pytest.mark.parametrize("channel", CHANNELS)
@pytest.mark.parametrize("path", PATHS)
async def test_core_delivery_format(generator, status, channel, path):
    """
    Pass (b): verifies the OUTPUT SHAPE is appropriate for delivery on the
    given channel (e.g. SMS length sanity, EMAIL is well-formed HTML,
    PUSH is short) for both the AI and fallback paths.
    """
    ctx = _build_context(status, channel)

    if path == "ai":
        _configure_ai_success(generator, status, channel)
        result = await generator.message_generate(
            context=ctx, template_key=f"{status}_{channel.lower()}", channel=channel
        )
        text = result if isinstance(result, str) else getattr(result, "output", str(result))
    else:
        _configure_forced_fallback(generator, reason="groq_error")
        result = await generator.message_generate(
            context=ctx, template_key=f"{status}_{channel.lower()}", channel=channel
        )
        text = getattr(result, "message", str(result))

    if channel == "EMAIL" and path == "ai":
        soup = BeautifulSoup(text, "html.parser")
        assert soup.find() is not None, "EMAIL AI output should be parseable HTML"
    elif channel == "SMS":
        assert len(text) <= 320, "SMS body should stay within a few segments"
    elif channel == "PUSH":
        assert len(text) <= 200, "PUSH body should be short enough for a notification"


# ---------------------------------------------------------------------------
# SECTION 2 — 13 EDGE CASE TESTS
# ---------------------------------------------------------------------------

async def test_edge_extremely_long_customer_name(generator):
    """
    Note: real CommunicationContext.customer_name has max_length=150, but
    pydantic v2 does NOT re-validate on plain attribute assignment (only
    validate_assignment=True would do that, and the schema doesn't set
    it). So this still exercises the generator/sanitizer's own defensive
    handling of an oversized value that slipped past construction-time
    validation. See test_edge_customer_name_exceeds_schema_max_length_raises
    below for the construction-time guarantee itself.
    """
    ctx = _build_context("assigned", "SMS")
    ctx.customer_name = "A" * 500
    _configure_ai_success(generator, "assigned", "SMS")
    result = await generator.message_generate(
        context=ctx, template_key="assigned_sms", channel="SMS"
    )
    assert result is not None


def test_edge_customer_name_exceeds_schema_max_length_raises():
    """
    The real CommunicationContext enforces max_length=150 on customer_name
    at construction time. This is a schema-level guarantee independent of
    AIMessageGenerator, so it's asserted directly against the real
    pydantic model.
    """
    data = dict(JOB_FIXTURES["assigned"])
    data["channel"] = "SMS"
    data["job_status"] = STATUS_TO_JOBSTATUS["assigned"]
    data["customer_name"] = "A" * 200
    with pytest.raises(ValidationError):
        CommunicationContext(**data)


async def test_edge_special_characters_in_additional_context(generator):
    """
    The real schema has no free-text "address" field — special-character
    handling is exercised via `additional_context`, the one free-text
    field CommunicationContext actually exposes.
    """
    ctx = _build_context("enroute", "EMAIL")
    ctx.additional_context = "12/B, \"Sunshine\" Apts, <Chennai> & Co."
    _configure_ai_success(generator, "enroute", "EMAIL")
    result = await generator.message_generate(
        context=ctx, template_key="enroute_email", channel="EMAIL"
    )
    assert result is not None


async def test_edge_missing_technician_name(generator):
    ctx = _build_context("created", "PUSH")
    ctx.technician_name = None
    _configure_ai_success(generator, "created", "PUSH")
    result = await generator.message_generate(
        context=ctx, template_key="created_push", channel="PUSH"
    )
    assert result is not None


async def test_edge_empty_template_key_raises(generator):
    ctx = _build_context("created", "SMS")
    with pytest.raises(ValueError):
        await generator.message_generate(context=ctx, template_key="   ", channel="SMS")


async def test_edge_whitespace_only_channel_raises(generator):
    ctx = _build_context("created", "SMS")
    with pytest.raises(ValueError):
        await generator.message_generate(context=ctx, template_key="k", channel="   ")


async def test_edge_channel_mismatch_raises(generator):
    ctx = _build_context("created", "SMS")
    with pytest.raises(ValueError):
        await generator.message_generate(context=ctx, template_key="k", channel="EMAIL")


async def test_edge_invalid_context_type_raises(generator):
    with pytest.raises(TypeError):
        await generator.message_generate(
            context={"not": "a context"}, template_key="k", channel="SMS"
        )
        
@pytest.mark.parametrize("failure_point", [
    "sanitize", "budget", "restore", "guardrail",
])
@pytest.mark.asyncio
async def test_edge_dependency_failure_forces_fallback(
    generator, budget_manager, monkeypatch, failure_point,
):
    context = _build_context("assigned", "SMS")
    fallback_result = _force_fallback(generator, context)
    _configure_ai_success(generator, "assigned", "SMS")

    def _raise(*a, **k):
        raise RuntimeError(f"{failure_point} failed")

    if failure_point == "sanitize":
        monkeypatch.setattr(pii_sanitizer, "sanitize_prompt", _raise)
    elif failure_point == "budget":
        budget_manager.check.side_effect = RuntimeError("budget service unavailable")
    elif failure_point == "restore":
        monkeypatch.setattr(pii_sanitizer, "restore_data", _raise)
    elif failure_point == "guardrail":
        generator.guardrail_pipeline.run.side_effect = RuntimeError("guardrail service unavailable")

    result = await generator.message_generate(
        context=context,
        template_key="assigned_sms",
        channel="SMS",
    )
    assert result is fallback_result
    if failure_point in ("budget",):
        generator.groq_client.generate_result.assert_not_called()

@pytest.mark.asyncio
async def test_edge_empty_channel_raises(generator):
    context = _build_context("created", "SMS")

    with pytest.raises(ValueError):
        await generator.message_generate(
            context=context,
            template_key="created_sms",
            channel="   ",
        )


@pytest.mark.asyncio
async def test_edge_context_sanitization_failure_forces_fallback(
    generator, monkeypatch,
):
    context = _build_context("assigned", "SMS")
    fallback_result = _force_fallback(generator, context)

    def fail_sanitize(*a, **k):
        raise RuntimeError("context sanitization failed")

    monkeypatch.setattr(pii_sanitizer, "sanitize", fail_sanitize)

    result = await generator.message_generate(
        context=context,
        template_key="assigned_sms",
        channel="SMS",
    )

    assert result is fallback_result
    generator.groq_client.generate_result.assert_not_called()


@pytest.mark.asyncio
async def test_edge_guardrail_rejection_forces_fallback(
    generator,
):
    context = _build_context(
        "cancelled",
        "SMS",
    )

    fallback_result = _force_fallback(
        generator,
        context,
    )

    _configure_ai_success(
        generator,
        "cancelled",
        "SMS",
    )

    generator.guardrail_pipeline.run.return_value = (
        SimpleNamespace(
            passed=False
        )
    )

    result = await generator.message_generate(
        context=context,
        template_key="cancelled_sms",
        channel="SMS",
    )

    assert result is fallback_result


@pytest.mark.parametrize("status,greeting,name", [
    ("onsite", "வணக்கம்", "இராம் குமார்"),
    ("completed", "नमस्ते", "राम कुमार"),
])
@pytest.mark.asyncio
async def test_edge_tamil_and_hindi_unicode_are_preserved(
    generator, status, greeting, name,
):
    context = _build_context(status, "SMS", customer_name=name)

    generator.guardrail_pipeline.run.return_value = SimpleNamespace(passed=True)
    generator.groq_client.generate_result.return_value = SimpleNamespace(
        text=f"{greeting} {{{{customer_name}}}}, your service request was updated."
    )

    result = await generator.message_generate(
        context=context,
        template_key=f"{status}_sms",
        channel="SMS",
    )

    decision = _extract_decision(result)

    assert isinstance(decision, CommunicationDecision)
    assert greeting in decision.message
    assert name in decision.message
    assert "{{customer_name}}" not in decision.message


# ============================================================================
# 8 PERFORMANCE TESTS
# ============================================================================


@pytest.mark.parametrize(
    "channel",
    CHANNELS,
)
@pytest.mark.asyncio
async def test_perf_ai_path_under_five_seconds(
    generator,
    channel,
):
    context = _build_context(
        "enroute",
        channel,
    )

    _configure_ai_success(
        generator,
        "enroute",
        channel,
    )

    if channel in {"EMAIL", "PUSH"}:
        generator.fallback_service.render.return_value = (
            _make_fallback_result(context)
        )

    start = time.perf_counter()

    await generator.message_generate(
        context=context,
        template_key=f"enroute_{channel.lower()}",
        channel=channel,
    )

    elapsed = time.perf_counter() - start

    assert elapsed < AI_LATENCY_BUDGET_SECONDS


@pytest.mark.asyncio
async def test_perf_ai_worst_case_payload_under_five_seconds(
    generator,
):
    context = _build_context(
        "completed",
        "EMAIL",
        customer_name="A" * 150,
        technician_name="T" * 150,
        job_title="J" * 200,
        additional_context="X" * 2000,
    )

    _configure_ai_success(
        generator,
        "completed",
        "EMAIL",
    )

    fake_fallback_cls.return_value.render.return_value = (
        fake_fallback_result
    )

    monkeypatch.setattr(
        f"{MODULE_PATH}.GuardrailFallbackService",
        fake_fallback_cls,
    )

    # ---------------------------------------------------------
    # IMPORTANT:
    # GroqClient is NOT mocked.
    # This creates the REAL GroqClient.
    # ---------------------------------------------------------

    generator = AIMessageGenerator(
        db=db_session,
        budget_manager=budget_manager,
    )

    # ---------------------------------------------------------
    # Allow real Groq response through guardrails
    # ---------------------------------------------------------

    generator.guardrail_pipeline = MagicMock()

    generator.guardrail_pipeline.run.return_value = SimpleNamespace(
        passed=True
    )

    # ---------------------------------------------------------
    # Build real communication context
    # ---------------------------------------------------------

    ctx = _build_context(
        "assigned",
        "SMS",
    )

    print()
    print("=" * 80)
    print("REAL GROQ API TEST")
    print("=" * 80)
    print(f"Job ID     : {ctx.job_id}")
    print(f"Customer   : {ctx.customer_name}")
    print(f"Technician : {ctx.technician_name}")
    print(f"Status     : {ctx.job_status}")
    print(f"Channel    : SMS")
    print("=" * 80)

    # ---------------------------------------------------------
    # Call REAL Groq
    # ---------------------------------------------------------

    start = time.perf_counter()

    result = await generator.message_generate(
        context=ctx,
        template_key="assigned_sms",
        channel="SMS",
    )

    elapsed = time.perf_counter() - start

    assert elapsed < FALLBACK_LATENCY_BUDGET_SECONDS


@pytest.mark.asyncio
async def test_perf_fallback_worst_case_payload_under_fifty_ms(
    generator,
    budget_manager,
):
    context = _build_context(
        "cancelled",
        "EMAIL",
        customer_name="A" * 150,
        technician_name="T" * 150,
        job_title="J" * 200,
        additional_context="X" * 2000,
    )

    _force_fallback(
        generator,
        context,
    )

    budget_manager.check.return_value = (
        SimpleNamespace(
            allowed=False
        )
    )

    start = time.perf_counter()

    await generator.message_generate(
        context=context,
        template_key="cancelled_email",
        channel="EMAIL",
    )

    elapsed = time.perf_counter() - start

    assert elapsed < FALLBACK_LATENCY_BUDGET_SECONDS


# ============================================================================
# EXPLICIT HTML VALIDATION
# ============================================================================
@pytest.mark.asyncio
async def test_coverage_final_prompt_sanitization_failure(
    generator,
    monkeypatch,
):
    context = _build_context("assigned", "SMS")

    fallback_result = _force_fallback(
        generator,
        context,
    )

    def fail_sanitize_prompt(*args, **kwargs):
        raise RuntimeError("final prompt sanitization failed")

    monkeypatch.setattr(
        pii_sanitizer,
        "sanitize_prompt",
        fail_sanitize_prompt,
    )

    result = await generator.message_generate(
        context=context,
        template_key="assigned_sms",
        channel="SMS",
    )

    assert result is fallback_result
    generator.groq_client.generate_result.assert_not_called()


@pytest.mark.asyncio
async def test_coverage_provider_failure(
    generator,
):
    context = _build_context("assigned", "SMS")

    fallback_result = _force_fallback(
        generator,
        context,
    )

    generator.groq_client.generate_result.side_effect = (
        RuntimeError("provider unavailable")
    )

    result = await generator.message_generate(
        context=context,
        template_key="assigned_sms",
        channel="SMS",
    )

    assert result is fallback_result


@pytest.mark.asyncio
async def test_coverage_empty_provider_response(
    generator,
):
    context = _build_context("assigned", "SMS")

    fallback_result = _force_fallback(
        generator,
        context,
    )

    generator.groq_client.generate_result.return_value = (
        SimpleNamespace(text="   ")
    )

    result = await generator.message_generate(
        context=context,
        template_key="assigned_sms",
        channel="SMS",
    )

    assert result is fallback_result


@pytest.mark.asyncio
async def test_coverage_formatter_failure(
    generator,
    monkeypatch,
):
    context = _build_context("assigned", "SMS")

    fallback_result = _force_fallback(
        generator,
        context,
    )

    monkeypatch.setattr(
        MessageOutputFormatter,
        "format",
        MagicMock(
            side_effect=RuntimeError(
                "formatter failure"
            )
        ),
    )

    _configure_ai_success(
        generator,
        "assigned",
        "SMS",
    )

    result = await generator.message_generate(
        context=context,
        template_key="assigned_sms",
        channel="SMS",
    )

    assert result is fallback_result


@pytest.mark.asyncio
async def test_coverage_decision_creation_failure(
    generator,
    monkeypatch,
):
    context = _build_context("assigned", "SMS")

    fallback_result = _force_fallback(
        generator,
        context,
    )

    _configure_ai_success(
        generator,
        "assigned",
        "SMS",
    )

    def fail_decision(*args, **kwargs):
        raise RuntimeError("decision creation failed")

    monkeypatch.setattr(
        "app.services.ai.FieldOpsAI.generators.ai_generator.CommunicationDecision",
        fail_decision,
    )

    result = await generator.message_generate(
        context=context,
        template_key="assigned_sms",
        channel="SMS",
    )

    assert result is fallback_result


@pytest.mark.asyncio
async def test_coverage_guardrail_rejection(
    generator,
):
    context = _build_context("assigned", "SMS")

    fallback_result = _force_fallback(
        generator,
        context,
    )

    _configure_ai_success(
        generator,
        "assigned",
        "SMS",
    )

    generator.guardrail_pipeline.run.return_value = (
        SimpleNamespace(
            passed=False
        )
    )

    result = await generator.message_generate(
        context=context,
        template_key="assigned_sms",
        channel="SMS",
    )

    assert result is fallback_result
    
    
def test_aigenerator_initialization(monkeypatch):
    from app.services.ai.FieldOpsAI.generators.ai_generator import AIGenerator

    orchestrator = MagicMock()

    monkeypatch.setattr(
        "app.services.ai.FieldOpsAI.generators.ai_generator.AIOrchestrator",
        lambda: orchestrator,
    )

    generator = AIGenerator()

    assert generator.orchestrator is orchestrator


def test_aigenerator_generate_delegates_to_orchestrator(monkeypatch):
    from app.services.ai.FieldOpsAI.generators.ai_generator import AIGenerator

    orchestrator = MagicMock()
    orchestrator.execute.return_value = "generated response"

    monkeypatch.setattr(
        "app.services.ai.FieldOpsAI.generators.ai_generator.AIOrchestrator",
        lambda: orchestrator,
    )

    generator = AIGenerator()

    context = {"job_id": "job-001"}

    result = generator.generate(
        task="communication",
        context=context,
    )

    assert result == "generated response"

    orchestrator.execute.assert_called_once_with(
        task="communication",
        context=context,
    )
    

