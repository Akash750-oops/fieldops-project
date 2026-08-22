from unittest.mock import Mock

import pytest

from app.services.ai.FieldOpsAI.agents.sentiment_engine import (
    SentimentEngine,
)
from app.services.ai.FieldOpsAI.schemas.sentiment import (
    SentimentContext,
    SentimentDecision,
)


def make_context(message: str) -> SentimentContext:
    return SentimentContext(
        channel="SMS",
        message=message,
    )


# =========================================================
# Basic sentiment classification
# =========================================================


def test_positive_sentiment():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        make_context(
            "The service is excellent, thank you"
        )
    )

    assert result.sentiment == "POSITIVE"
    assert result.emotion == "HAPPY"
    assert result.urgency == "LOW"


def test_negative_sentiment():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        make_context(
            "The service is terrible and not working"
        )
    )

    assert result.sentiment == "NEGATIVE"
    assert result.emotion == "FRUSTRATED"
    assert result.urgency == "HIGH"


def test_neutral_sentiment():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        make_context(
            "Please send me the appointment status"
        )
    )

    assert result.sentiment == "NEUTRAL"
    assert result.emotion == "CALM"
    assert result.urgency == "LOW"


def test_mixed_sentiment():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        make_context(
            "The technician was great but the AC is still broken"
        )
    )

    assert result.sentiment == "MIXED"
    assert result.emotion == "CONCERNED"
    assert result.urgency == "HIGH"


# =========================================================
# Confidence validation
# =========================================================


def test_confidence_is_within_valid_range():
    engine = SentimentEngine()

    messages = [
        "The service is excellent",
        "The service is terrible",
        "The appointment is scheduled",
        "The technician was great but the AC is broken",
    ]

    for message in messages:
        result = engine._keyword_fallback(
            make_context(message)
        )

        assert 0.0 <= result.confidence <= 1.0


def test_confidence_is_rounded():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        make_context(
            "The technician was great but the AC is still broken"
        )
    )

    assert result.confidence == 0.78


# =========================================================
# Human intervention
# =========================================================


def test_manager_request_requires_human():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        make_context(
            "I want to speak to a manager"
        )
    )

    assert result.requires_human is True


def test_safety_issue_requires_human():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        make_context(
            "There is a safety problem with the equipment"
        )
    )

    assert result.requires_human is True
    assert result.urgency == "HIGH"


def test_angry_customer_requires_human():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        make_context(
            "I am extremely angry about this service"
        )
    )

    assert result.sentiment == "NEGATIVE"
    assert result.emotion == "ANGRY"
    assert result.requires_human is True


# =========================================================
# Summary
# =========================================================


def test_positive_summary_is_present():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        make_context(
            "The service was excellent"
        )
    )

    assert result.summary
    assert len(result.summary.split()) <= 30


def test_negative_summary_is_present():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        make_context(
            "The service is terrible and not working"
        )
    )

    assert result.summary
    assert len(result.summary.split()) <= 30


# =========================================================
# AI failure -> keyword fallback
# =========================================================


def test_ai_failure_uses_keyword_fallback():
    mock_orchestrator = Mock()

    mock_orchestrator.execute.side_effect = RuntimeError(
        "AI provider unavailable"
    )

    engine = SentimentEngine(
        orchestrator=mock_orchestrator
    )

    result = engine.analyze(
        make_context(
            "The service is terrible and not working"
        )
    )

    assert isinstance(result, SentimentDecision)
    assert result.sentiment == "NEGATIVE"
    assert result.urgency == "HIGH"

    mock_orchestrator.execute.assert_called_once()


# =========================================================
# AI success path
# =========================================================


def test_ai_success_returns_ai_decision():
    mock_orchestrator = Mock()

    expected = SentimentDecision(
        sentiment="POSITIVE",
        emotion="HAPPY",
        urgency="LOW",
        requires_human=False,
        confidence=0.95,
        summary="Customer expresses positive feedback about the service.",
    )

    mock_orchestrator.execute.return_value = expected

    engine = SentimentEngine(
        orchestrator=mock_orchestrator
    )

    result = engine.analyze(
        make_context(
            "The service is excellent"
        )
    )

    assert result == expected
    assert result.sentiment == "POSITIVE"
    assert result.confidence == 0.95

    mock_orchestrator.execute.assert_called_once()


# =========================================================
# Supported channels
# =========================================================


@pytest.mark.parametrize(
    "channel",
    [
        "EMAIL",
        "SMS",
        "CHAT",
        "WHATSAPP",
        "SUPPORT_TICKET",
        "DISPATCH_NOTE",
    ],
)
def test_supported_channels(channel):
    context = SentimentContext(
        channel=channel,
        message="The service is good",
    )

    engine = SentimentEngine()

    result = engine._keyword_fallback(context)

    assert result.sentiment == "POSITIVE"


def test_positive_intensifier_increases_score():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        SentimentContext(
            channel="SMS",
            message="The service is very excellent",
            language="en",
        )
    )

    assert result.sentiment == "POSITIVE"


def test_disappointed_emotion():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        SentimentContext(
            channel="SMS",
            message="I am disappointed with the service",
            language="en",
        )
    )

    assert result.sentiment == "NEGATIVE"
    assert result.emotion == "DISAPPOINTED"


def test_medium_urgency():
    engine = SentimentEngine()

    result = engine._keyword_fallback(
        SentimentContext(
            channel="SMS",
            message="There is a problem with the service",
            language="en",
        )
    )

    assert result.urgency == "MEDIUM"
