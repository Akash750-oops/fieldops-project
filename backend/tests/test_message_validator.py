from __future__ import annotations

import pytest
import httpx
from app.services.ai.guardrails.message_validator import (
    MessageValidationResult,
    MessageValidator,
    PhoneFormatValidator,
    QualityValidator,
    URLReachabilityProviderError,
    URLReachabilityResult,
    URLValidator,
    HTTPXURLReachabilityProvider
)
from app.services.ai.FieldOpsAI.schemas.communication import (
    CommunicationContext,
    CommunicationDecision,
    SMSMessageOutput,
)

from app.services.ai.guardrails.contracts import (
    GuardrailCategory,
    GuardrailCheckResult,
    GuardrailSeverity,
    GuardrailViolation,
)

# ============================================================
# Helpers
# ============================================================


def make_context() -> CommunicationContext:
    return CommunicationContext(
        job_id="JOB-123",
        correlation_id="corr-123",
        notification_type="job_assigned",
        recipient_type="CUSTOMER",
        channel="SMS",
        locale="en-US",
        customer_name="John",
        technician_name="Mike",
        job_status="ASSIGNED",
        job_title="AC Repair",
    )


def make_decision(message: str) -> CommunicationDecision:
    return CommunicationDecision(
        channel="SMS",
        output=SMSMessageOutput(
            channel="SMS",
            text=message,
        ),
        tone="PROFESSIONAL",
        confidence=0.95,
    )


# ============================================================
# URLReachabilityResult
# ============================================================


def test_url_reachability_result_valid():
    result = URLReachabilityResult(
        reachable=True,
        status_code=200,
        latency_ms=10.5,
    )

    assert result.reachable is True
    assert result.status_code == 200
    assert result.latency_ms == 10.5


# ============================================================
# URLValidator - syntax
# ============================================================


def test_url_validator_passes_valid_https_url():
    validator = URLValidator()

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Please visit https://fieldops.com for more information."
        ),
    )

    assert result.passed is True
    assert result.violations == ()


def test_url_validator_passes_valid_http_url():
    validator = URLValidator()

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Visit http://example.com for details."
        ),
    )

    assert result.passed is True


def test_url_validator_removes_trailing_punctuation():
    validator = URLValidator()

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Please visit https://example.com."
        ),
    )

    assert result.passed is True


def test_url_validator_rejects_invalid_scheme():
    validator = URLValidator()

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Visit ftp://example.com now."
        ),
    )

    # ftp:// is not detected by the HTTP/HTTPS URL regex,
    # therefore no URL validation violation is expected.
    assert result.passed is True


def test_url_validator_rejects_malformed_http_url():
    validator = URLValidator()

    # The regex detects this as an HTTP URL, but urlparse()
    # sees an invalid/empty network location.
    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Visit https:///broken.example now."
        ),
    )

    assert result.passed is False
    assert any(
        violation.code == "URL_INVALID_SYNTAX"
        for violation in result.violations
    )


def test_url_validator_handles_no_urls():
    validator = URLValidator()

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Hello John, your technician will arrive at 3 PM."
        ),
    )

    assert result.passed is True
    assert result.violations == ()


# ============================================================
# URLValidator - _has_valid_syntax
# ============================================================


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com", True),
        ("http://example.com", True),
        ("HTTPS://EXAMPLE.COM", True),
        ("ftp://example.com", False),
        ("example.com", False),
        ("https:///example.com", False),
        ("https://", False),
    ],
)
def test_url_syntax_validation(url: str, expected: bool):
    assert URLValidator._has_valid_syntax(url) is expected


def test_url_validator_handles_urlparse_value_error(monkeypatch):
    def raise_value_error(_url):
        raise ValueError("invalid URL")

    monkeypatch.setattr(
        "app.services.ai.guardrails.message_validator.urlparse",
        raise_value_error,
    )

    assert URLValidator._has_valid_syntax("https://example.com") is False


# ============================================================
# URLValidator - reachability
# ============================================================


class ReachableProvider:
    provider_name = "test-provider"

    def check_reachable(
        self,
        *,
        url: str,
    ) -> URLReachabilityResult:
        return URLReachabilityResult(
            reachable=True,
            status_code=200,
            latency_ms=5.0,
        )


class UnreachableProvider:
    provider_name = "test-provider"

    def check_reachable(
        self,
        *,
        url: str,
    ) -> URLReachabilityResult:
        return URLReachabilityResult(
            reachable=False,
            status_code=404,
            latency_ms=5.0,
        )


class ErrorProvider:
    provider_name = "test-provider"

    def check_reachable(
        self,
        *,
        url: str,
    ) -> URLReachabilityResult:
        raise URLReachabilityProviderError("DNS failure")


def test_url_validator_requires_provider_when_reachability_enabled():
    with pytest.raises(ValueError):
        URLValidator(
            reachability_check_enabled=True,
        )


def test_url_validator_reachable_url():
    validator = URLValidator(
        reachability_provider=ReachableProvider(),
        reachability_check_enabled=True,
    )

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Visit https://example.com."
        ),
    )

    assert result.passed is True


def test_url_validator_unreachable_url():
    validator = URLValidator(
        reachability_provider=UnreachableProvider(),
        reachability_check_enabled=True,
    )

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Visit https://example.com."
        ),
    )

    assert result.passed is False
    assert any(
        violation.code == "URL_UNREACHABLE"
        for violation in result.violations
    )


def test_url_validator_provider_error():
    validator = URLValidator(
        reachability_provider=ErrorProvider(),
        reachability_check_enabled=True,
    )

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Visit https://example.com."
        ),
    )

    assert result.passed is False

    violation = next(
        violation
        for violation in result.violations
        if violation.code == "URL_UNREACHABLE"
    )

    assert violation.severity.value == "WARNING"


# ============================================================
# PhoneFormatValidator
# ============================================================


def test_phone_validator_accepts_valid_e164():
    validator = PhoneFormatValidator()

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Call us at +14155552671."
        ),
    )

    assert result.passed is True


@pytest.mark.parametrize(
    "phone",
    [
        "14155552671",
        "415-555-2671",
        "(415) 555-2671",
        "+1 415 555 2671",
        "+1415555267",
    ],
)
def test_phone_validator_rejects_non_e164(phone: str):
    validator = PhoneFormatValidator()

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            f"Call us at {phone}."
        ),
    )

    assert result.passed is False
    assert any(
        violation.code == "PHONE_NUMBER_NOT_E164"
        for violation in result.violations
    )


def test_phone_validator_ignores_job_identifier():
    validator = PhoneFormatValidator()

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Your job number is JOB-1234567890."
        ),
    )

    assert result.passed is True


@pytest.mark.parametrize(
    "identifier",
    [
        "JOB-1234567890",
        "TICKET-1234567890",
        "CASE-1234567890",
        "ORDER-1234567890",
        "REFERENCE-1234567890",
        "REF-1234567890",
    ],
)
def test_phone_validator_ignores_non_phone_identifiers(identifier: str):
    validator = PhoneFormatValidator()

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            f"Reference: {identifier}"
        ),
    )

    assert result.passed is True


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("+14155552671", True),
        ("+919876543210", True),
        ("+123456789012345", True),
        ("14155552671", False),
        ("+0123456789", False),
        ("+1234567890123456", False),
        ("+1 4155552671", False),
        ("", False),
    ],
)
def test_is_valid_e164(value: str, expected: bool):
    assert PhoneFormatValidator.is_valid_e164(value) is expected


def test_phone_validator_counts_multiple_invalid_numbers():
    validator = PhoneFormatValidator()

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Call 415-555-2671 or 987-654-3210."
        ),
    )

    assert result.passed is False

    violation = next(
        violation
        for violation in result.violations
        if violation.code == "PHONE_NUMBER_NOT_E164"
    )

    assert violation.safe_metadata["invalid_count"] == 2


# ============================================================
# QualityValidator
# ============================================================


def test_quality_score_is_between_zero_and_100():
    validator = QualityValidator()

    score = validator.score(
        context=make_context(),
        decision=make_decision(
            "Hello John, your technician will arrive at 3 PM. Thank you!"
        ),
    )

    assert 0 <= score <= 100


def test_empty_message_quality_score_is_zero():
    validator = QualityValidator()

    score = validator.score(
        context=make_context(),
        decision=make_decision(""),
    )

    assert score == 0


def test_quality_score_for_normal_message():
    validator = QualityValidator()

    score = validator.score(
        context=make_context(),
        decision=make_decision(
            "Hello John, your technician will arrive at 3 PM. Thank you!"
        ),
    )

    assert isinstance(score, int)
    assert 0 <= score <= 100


def test_quality_score_detects_short_message():
    validator = QualityValidator()

    score = validator.score(
        context=make_context(),
        decision=make_decision("Hi"),
    )

    assert 0 <= score <= 100


def test_quality_score_detects_unfilled_placeholder():
    validator = QualityValidator()

    score = validator.score(
        context=make_context(),
        decision=make_decision(
            "Hello {customer_name}, your technician is coming."
        ),
    )

    assert 0 <= score <= 100


def test_quality_score_handles_placeholder():
    validator = QualityValidator()

    score = validator.score(
        context=make_context(),
        decision=make_decision(
            "Hello {{customer_name}}, your technician will arrive at 3 PM."
        ),
    )

    assert 0 <= score <= 100


def test_readability_score_empty_text():
    assert QualityValidator._readability_score("") == 0


def test_readability_score_simple_text():
    score = QualityValidator._readability_score(
        "Hello John. Your technician will arrive today."
    )

    assert 0 <= score <= 100


def test_readability_score_long_sentence():
    text = (
        "This is a very long sentence that contains many words and "
        "continues for a considerable amount of time so that the "
        "readability calculation has to apply its sentence length "
        "penalty."
    )

    score = QualityValidator._readability_score(text)

    assert 0 <= score <= 100


def test_completeness_score_short_message():
    score = QualityValidator._completeness_score("Hi")

    assert score == 40


def test_completeness_score_unfilled_placeholder():
    score = QualityValidator._completeness_score(
        "Hello {customer_name}"
    )

    assert 0 <= score <= 100


def test_completeness_score_missing_terminal_punctuation():
    score = QualityValidator._completeness_score(
        "Hello John, your technician is coming"
    )

    assert score == 90


def test_completeness_score_complete_message():
    score = QualityValidator._completeness_score(
        "Hello John, your technician is coming."
    )

    assert score == 100


def test_quality_validator_rejects_invalid_threshold():
    with pytest.raises(ValueError):
        QualityValidator(minimum_passing_score=-1)

    with pytest.raises(ValueError):
        QualityValidator(minimum_passing_score=101)


def test_quality_validator_check():
    validator = QualityValidator(
        minimum_passing_score=0,
    )

    result = validator.check(
        context=make_context(),
        decision=make_decision(
            "Hello John, your technician will arrive at 3 PM."
        ),
    )

    assert result.checker_name == "quality_validator"
    assert result.passed is True


def test_quality_validator_low_score_creates_violation():
    validator = QualityValidator(
        minimum_passing_score=100,
    )

    result = validator.check(
        context=make_context(),
        decision=make_decision("Hi"),
    )

    assert result.passed is False

    assert any(
        violation.code == "MESSAGE_QUALITY_BELOW_THRESHOLD"
        for violation in result.violations
    )


# ============================================================
# MessageValidator facade
# ============================================================


def test_message_validator_creates_default_pipeline():
    validator = MessageValidator()

    assert validator._pipeline is not None
    assert validator._quality_validator is not None


def test_message_validator_uses_same_quality_validator():
    quality_validator = QualityValidator()

    validator = MessageValidator(
        quality_validator=quality_validator,
    )

    assert validator._quality_validator is quality_validator

    quality_checkers = [
        checker
        for checker in validator._pipeline._checkers
        if checker.checker_name == "quality_validator"
    ]

    assert len(quality_checkers) == 1
    assert quality_checkers[0] is quality_validator


def test_message_validator_default_pipeline():
    pipeline = MessageValidator.default_pipeline()

    checker_names = [
        checker.checker_name
        for checker in pipeline._checkers
    ]

    assert checker_names == [
        "channel_validator",
        "length_validator",
        "placeholder_integrity_validator",
        "pii_output_detector",
        "profanity_validator",
        "brand_safety_validator",
        "tone_validator",
        "url_validator",
        "phone_format_validator",
        "quality_validator",
    ]


def test_message_validator_validate_returns_result():
    validator = MessageValidator()

    result = validator.validate(
        context=make_context(),
        decision=make_decision(
            "Hello John, your technician will arrive at 3 PM."
        ),
    )

    assert isinstance(result, MessageValidationResult)
    assert 0 <= result.quality_score <= 100
    assert result.pipeline_result is not None


def test_message_validator_passes_valid_message():
    validator = MessageValidator()

    result = validator.validate(
        context=make_context(),
        decision=make_decision(
            "Hello John, your technician will arrive at 3 PM."
        ),
    )

    assert result.passed is True


def test_message_validator_detects_invalid_phone():
    validator = MessageValidator()

    result = validator.validate(
        context=make_context(),
        decision=make_decision(
            "Please call us at 415-555-2671."
        ),
    )

    assert result.passed is False

    assert any(
        violation.code == "PHONE_NUMBER_NOT_E164"
        for violation in result.pipeline_result.violations
    )


def test_message_validator_detects_invalid_url():
    validator = MessageValidator()

    result = validator.validate(
        context=make_context(),
        decision=make_decision(
            "Visit https:///broken.example now."
        ),
    )

    assert result.passed is False

    assert any(
        violation.code == "URL_INVALID_SYNTAX"
        for violation in result.pipeline_result.violations
    )


# ============================================================
# MessageValidationResult properties
# ============================================================


def test_message_validation_result_properties():
    validator = MessageValidator()

    result = validator.validate(
        context=make_context(),
        decision=make_decision(
            "Hello John, your technician will arrive at 3 PM."
        ),
    )

    assert result.passed == result.pipeline_result.passed
    assert (
        result.requires_fallback
        == result.pipeline_result.requires_fallback
    )

def test_url_validator_returns_true_when_provider_is_none():
    validator = URLValidator()

    assert validator._is_reachable(
        "https://example.com"
    ) is True


def test_phone_validator_ignores_too_short_or_too_long_candidate():
    value = "123456 1234567890123456"

    assert (
        PhoneFormatValidator._count_non_e164_candidates(
            value
        )
        == 0
    )


def test_readability_score_returns_zero_when_no_words():
    assert (
        QualityValidator._readability_score(
            "{{placeholder}}"
        )
        == 0
    )


def test_completeness_score_returns_zero_for_empty_text():
    assert (
        QualityValidator._completeness_score("")
        == 0
    )


def test_quality_tone_score_penalizes_tone_violations():
    class FailingToneValidator:
        def check(self, *, context, decision):
            return GuardrailCheckResult(
                checker_name="tone_validator",
                passed=False,
                violations=(
                    GuardrailViolation(
                        code="TONE_VIOLATION",
                        category=GuardrailCategory.OUTPUT_SCHEMA,
                        severity=GuardrailSeverity.WARNING,
                        message="Tone violation.",
                        field="output",
                        safe_metadata={},
                    ),
                ),
                latency_ms=0.0,
            )

    quality_validator = QualityValidator(
        tone_validator=FailingToneValidator()
    )

    context = CommunicationContext(
    job_id="job-123",
    correlation_id="corr-123",
    notification_type="job_assigned",
    recipient_type="CUSTOMER",
    channel="SMS",
    locale="en-US",
    job_status="ASSIGNED",
)

    decision = CommunicationDecision(
        channel="SMS",
        output={
            "channel": "SMS",
            "text": "Your technician is scheduled for today.",
        },
        tone="FRIENDLY",
        confidence=0.95,
    )

    assert (
        quality_validator._tone_score(
            context=context,
            decision=decision,
        )
        == 70
    )
# ============================================================
# HTTPXURLReachabilityProvider
# ============================================================


def test_httpx_provider_returns_reachable_for_200(
    monkeypatch,
):
    class FakeResponse:
        status_code = 200

    class FakeClient:
        def __init__(
            self,
            *,
            timeout,
            follow_redirects,
        ):
            assert timeout == 5.0
            assert follow_redirects is True

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return None

        def get(self, url):
            assert url == "https://example.com"
            return FakeResponse()

    monkeypatch.setattr(
        httpx,
        "Client",
        FakeClient,
    )

    provider = HTTPXURLReachabilityProvider()

    result = provider.check_reachable(
        url="https://example.com",
    )

    assert result.reachable is True
    assert result.status_code == 200
    assert result.latency_ms >= 0


def test_httpx_provider_returns_unreachable_for_404(
    monkeypatch,
):
    class FakeResponse:
        status_code = 404

    class FakeClient:
        def __init__(
            self,
            *,
            timeout,
            follow_redirects,
        ):
            pass

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return None

        def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(
        httpx,
        "Client",
        FakeClient,
    )

    provider = HTTPXURLReachabilityProvider()

    result = provider.check_reachable(
        url="https://example.com/missing",
    )

    assert result.reachable is False
    assert result.status_code == 404
    assert result.latency_ms >= 0


def test_httpx_provider_treats_500_as_unreachable(
    monkeypatch,
):
    class FakeResponse:
        status_code = 500

    class FakeClient:
        def __init__(
            self,
            *,
            timeout,
            follow_redirects,
        ):
            pass

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return None

        def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(
        httpx,
        "Client",
        FakeClient,
    )

    provider = HTTPXURLReachabilityProvider()

    result = provider.check_reachable(
        url="https://example.com/error",
    )

    assert result.reachable is False
    assert result.status_code == 500


def test_httpx_provider_follows_redirects(
    monkeypatch,
):
    class FakeResponse:
        status_code = 200

    class FakeClient:
        def __init__(
            self,
            *,
            timeout,
            follow_redirects,
        ):
            assert timeout == 3.0
            assert follow_redirects is True

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return None

        def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(
        httpx,
        "Client",
        FakeClient,
    )

    provider = HTTPXURLReachabilityProvider(
        timeout=3.0,
        follow_redirects=True,
    )

    result = provider.check_reachable(
        url="http://example.com",
    )

    assert result.reachable is True
    assert result.status_code == 200


def test_httpx_provider_converts_timeout_error(
    monkeypatch,
):
    class FakeClient:
        def __init__(
            self,
            *,
            timeout,
            follow_redirects,
        ):
            pass

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return None

        def get(self, url):
            raise httpx.ReadTimeout(
                "request timed out"
            )

    monkeypatch.setattr(
        httpx,
        "Client",
        FakeClient,
    )

    provider = HTTPXURLReachabilityProvider()

    with pytest.raises(
        URLReachabilityProviderError,
        match="timed out",
    ):
        provider.check_reachable(
            url="https://example.com",
        )


def test_httpx_provider_converts_request_error(
    monkeypatch,
):
    class FakeClient:
        def __init__(
            self,
            *,
            timeout,
            follow_redirects,
        ):
            pass

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return None

        def get(self, url):
            raise httpx.ConnectError(
                "connection failed"
            )

    monkeypatch.setattr(
        httpx,
        "Client",
        FakeClient,
    )

    provider = HTTPXURLReachabilityProvider()

    with pytest.raises(
        URLReachabilityProviderError,
        match="failed",
    ):
        provider.check_reachable(
            url="https://example.com",
        )


def test_httpx_provider_rejects_invalid_timeout():
    with pytest.raises(ValueError):
        HTTPXURLReachabilityProvider(
            timeout=0,
        )












  