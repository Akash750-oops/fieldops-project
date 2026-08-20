from unittest.mock import MagicMock

import pytest

from app.services.ai.FieldOpsAI.agents.intent_engine import IntentEngine
from app.services.ai.FieldOpsAI.schemas.intent import IntentContext, IntentResult


class FakeOrchestrator:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def execute(self, **kwargs):
        if self.error:
            raise self.error
        return self.result


def make_context(message: str, language: str = "en") -> IntentContext:
    return IntentContext(
        message=message,
        language=language,
    )


# ==========================================================
# AI CLASSIFICATION
# ==========================================================


def test_ai_classifies_status_inquiry():
    orchestrator = FakeOrchestrator(
        result=IntentResult(
            intent="STATUS_INQUIRY",
            confidence=0.99,
            requires_human=False,
        )
    )

    engine = IntentEngine(orchestrator=orchestrator)

    result = engine.recognize(
        make_context("Where is my technician?")
    )

    assert result.intent == "STATUS_INQUIRY"
    assert result.confidence == 0.99
    assert result.requires_human is False


def test_ai_classifies_complaint():
    orchestrator = FakeOrchestrator(
        result=IntentResult(
            intent="COMPLAINT",
            confidence=0.99,
            requires_human=False,
        )
    )

    engine = IntentEngine(orchestrator=orchestrator)

    result = engine.recognize(
        make_context("The technician did not fix my problem.")
    )

    assert result.intent == "COMPLAINT"


def test_ai_classifies_compliment():
    orchestrator = FakeOrchestrator(
        result=IntentResult(
            intent="COMPLIMENT",
            confidence=0.99,
            requires_human=False,
        )
    )

    engine = IntentEngine(orchestrator=orchestrator)

    result = engine.recognize(
        make_context("Thank you, the technician did a great job.")
    )

    assert result.intent == "COMPLIMENT"


def test_ai_classifies_cancellation():
    orchestrator = FakeOrchestrator(
        result=IntentResult(
            intent="CANCELLATION",
            confidence=0.99,
            requires_human=False,
        )
    )

    engine = IntentEngine(orchestrator=orchestrator)

    result = engine.recognize(
        make_context("I want to cancel my appointment.")
    )

    assert result.intent == "CANCELLATION"


def test_ai_classifies_general_question():
    orchestrator = FakeOrchestrator(
        result=IntentResult(
            intent="GENERAL_QUESTION",
            confidence=0.90,
            requires_human=False,
        )
    )

    engine = IntentEngine(orchestrator=orchestrator)

    result = engine.recognize(
        make_context("What services do you provide?")
    )

    assert result.intent == "GENERAL_QUESTION"


def test_ai_classifies_escalation_request():
    orchestrator = FakeOrchestrator(
        result=IntentResult(
            intent="ESCALATION_REQUEST",
            confidence=0.99,
            requires_human=False,
        )
    )

    engine = IntentEngine(orchestrator=orchestrator)

    result = engine.recognize(
        make_context("I want to speak to a manager.")
    )

    assert result.intent == "ESCALATION_REQUEST"


# ==========================================================
# KEYWORD FALLBACK
# ==========================================================


def test_fallback_classifies_cancellation():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context("Please cancel my appointment.")
    )

    assert result.intent == "CANCELLATION"
    assert 0.0 <= result.confidence <= 1.0


def test_fallback_classifies_complaint():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context("The service is terrible and still not fixed.")
    )

    assert result.intent == "COMPLAINT"


def test_fallback_classifies_compliment():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context("Thank you, great service!")
    )

    assert result.intent == "COMPLIMENT"


def test_fallback_classifies_status():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context("Where is my technician?")
    )

    assert result.intent == "STATUS_INQUIRY"


def test_fallback_classifies_escalation():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context("I want to speak to a manager.")
    )

    assert result.intent == "ESCALATION_REQUEST"


def test_fallback_general_question_requires_human():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context("Can you help me?")
    )

    assert result.intent == "GENERAL_QUESTION"
    assert result.confidence < 0.70
    assert result.requires_human is True


# ==========================================================
# CONFIDENCE THRESHOLD
# ==========================================================


def test_confidence_below_070_requires_human():
    orchestrator = FakeOrchestrator(
        result=IntentResult(
            intent="GENERAL_QUESTION",
            confidence=0.69,
            requires_human=True,
        )
    )

    engine = IntentEngine(orchestrator=orchestrator)

    result = engine.recognize(
        make_context("I have a question.")
    )

    assert result.confidence == 0.69
    assert result.requires_human is True


def test_confidence_at_070_does_not_require_human():
    orchestrator = FakeOrchestrator(
        result=IntentResult(
            intent="GENERAL_QUESTION",
            confidence=0.70,
            requires_human=False,
        )
    )

    engine = IntentEngine(orchestrator=orchestrator)

    result = engine.recognize(
        make_context("I have a question.")
    )

    assert result.confidence == 0.70
    assert result.requires_human is False


# ==========================================================
# MULTI-LANGUAGE INPUT
# ==========================================================


def test_hindi_cancellation_fallback():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context(
            "मैं अपनी अपॉइंटमेंट रद्द करना चाहता हूँ।",
            "hi",
        )
    )

    assert result.intent == "CANCELLATION"
    assert result.confidence == 0.85
    assert result.requires_human is False

# ==========================================================
# MULTI-LANGUAGE FALLBACK COVERAGE
# ==========================================================


def test_spanish_cancellation_fallback():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context(
            "Quiero cancelar mi cita.",
            "es",
        )
    )

    assert result.intent == "CANCELLATION"
    assert result.confidence == 0.85
    assert result.requires_human is False


def test_tamil_cancellation_fallback():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context(
            "எனது அப்பாயின்ட்மெண்ட்டை ரத்து செய்ய வேண்டும்.",
            "ta",
        )
    )

    assert result.intent == "CANCELLATION"
    assert result.confidence == 0.85
    assert result.requires_human is False


def test_hindi_cancellation_fallback():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context(
            "मैं अपनी अपॉइंटमेंट रद्द करना चाहता हूँ।",
            "hi",
        )
    )

    assert result.intent == "CANCELLATION"
    assert result.confidence == 0.85
    assert result.requires_human is False


def test_spanish_complaint_fallback():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context(
            "El servicio es muy malo.",
            "es",
        )
    )

    assert result.intent == "COMPLAINT"
    assert result.confidence == 0.80
    assert result.requires_human is False


def test_tamil_compliment_fallback():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context(
            "நன்றி, சிறந்த சேவை.",
            "ta",
        )
    )

    assert result.intent == "COMPLIMENT"
    assert result.confidence == 0.80
    assert result.requires_human is False


def test_hindi_status_fallback():
    engine = IntentEngine(
        orchestrator=FakeOrchestrator(
            error=RuntimeError("AI unavailable")
        )
    )

    result = engine.recognize(
        make_context(
            "तकनीशियन कब आएगा?",
            "hi",
        )
    )

    assert result.intent == "STATUS_INQUIRY"
    assert result.confidence == 0.75
    assert result.requires_human is False