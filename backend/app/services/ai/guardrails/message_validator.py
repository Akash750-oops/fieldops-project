from __future__ import annotations

import re
from time import perf_counter
from typing import Final, Protocol, runtime_checkable
from urllib.parse import urlparse
import httpx

from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.FieldOpsAI.schemas.communication import (
    CommunicationContext,
    CommunicationDecision,
    output_text_for_validation,
)
from app.services.ai.guardrails.brand_safety_validator import (
    BrandSafetyValidator,
)
from app.services.ai.guardrails.channel_validator import ChannelValidator
from app.services.ai.guardrails.contracts import (
    GuardrailCategory,
    GuardrailCheckResult,
    GuardrailPipelineResult,
    GuardrailSeverity,
    GuardrailViolation,
)
from app.services.ai.guardrails.length_validator import LengthValidator
from app.services.ai.guardrails.pii_output_detector import PIIOutputDetector
from app.services.ai.guardrails.pipeline import GuardrailPipeline
from app.services.ai.guardrails.placeholder_integrity_validator import (
    PlaceholderIntegrityValidator,
)
from app.services.ai.guardrails.profanity_validator import ProfanityValidator
from app.services.ai.guardrails.tone_validator import ToneValidator


# ==========================================================
# URL Validation
# ==========================================================


class URLReachabilityResult(BaseModel):
    """
    Structured response returned by an optional reachability
    provider. Never contains the checked URL itself.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        frozen=True,
    )

    reachable: bool = Field(
        ...,
        description="Whether the URL responded successfully.",
    )

    status_code: int | None = Field(
        default=None,
        description="HTTP status code, when available.",
    )

    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Reachability check execution time.",
    )


class URLReachabilityProviderError(RuntimeError):
    """
    Raised when an enabled reachability provider cannot return a
    valid result (timeout, DNS failure, connection error, etc.).
    """


@runtime_checkable
class URLReachabilityProvider(Protocol):
    """
    Interface for optional URL reachability checks.

    Implementations are responsible for enforcing their own
    bounded timeout. This validator never assumes a timeout is
    applied on its behalf.
    """

    provider_name: str

    def check_reachable(self, *, url: str) -> URLReachabilityResult:
        """
        Check whether the supplied URL is reachable.

        Raises
        ------
        URLReachabilityProviderError
            If the check cannot be completed safely.
        """

        ...

class HTTPXURLReachabilityProvider:
    """
    URL reachability provider backed by HTTPX.

    The provider owns its timeout and converts HTTPX failures into
    URLReachabilityProviderError so callers do not need to know
    about HTTPX-specific exceptions.
    """

    provider_name: Final[str] = "httpx"

    def __init__(
        self,
        *,
        timeout: float = 5.0,
        follow_redirects: bool = True,
    ) -> None:
        """
        Parameters
        ----------
        timeout
            Maximum time allowed for the HTTP request.

        follow_redirects
            Whether HTTP redirects should be followed.
        """

        if timeout <= 0:
            raise ValueError("timeout must be greater than zero.")

        self._timeout = timeout
        self._follow_redirects = follow_redirects

    def check_reachable(
        self,
        *,
        url: str,
    ) -> URLReachabilityResult:
        """
        Perform an HTTP request and return structured reachability data.

        2xx and 3xx responses are considered reachable.

        HTTP errors such as 4xx and 5xx responses are considered
        unreachable but still return a normal result.

        Network, timeout, and HTTPX request errors are converted
        into URLReachabilityProviderError.
        """

        started_at = perf_counter()

        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=self._follow_redirects,
            ) as client:
                response = client.get(url)

        except httpx.TimeoutException as exc:
            raise URLReachabilityProviderError(
                "URL reachability check timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise URLReachabilityProviderError(
                "URL reachability check failed."
            ) from exc

        latency_ms = (
            perf_counter() - started_at
        ) * 1000

        return URLReachabilityResult(
            reachable=200 <= response.status_code < 400,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
class URLValidator:
    """
    Detect and validate URLs in generated communication.
    """

    checker_name: Final[str] = "url_validator"

    URL_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\bhttps?://[^\s<>\"']+",
        re.IGNORECASE,
    )

    ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset(
        {"http", "https"}
    )

    def __init__(
        self,
        *,
        reachability_provider: URLReachabilityProvider | None = None,
        reachability_check_enabled: bool = False,
    ) -> None:
        """
        Parameters
        ----------
        reachability_provider
            Optional provider used to check live reachability.

        reachability_check_enabled
            When False (default), only local syntax validation
            runs - no network calls.

            When True, every detected URL is additionally passed
            to the injected provider, which owns its own timeout.
        """

        if (
            reachability_check_enabled
            and reachability_provider is None
        ):
            raise ValueError(
                "A reachability provider is required when "
                "reachability checking is enabled."
            )

        self._reachability_provider = reachability_provider
        self._reachability_check_enabled = (
            reachability_check_enabled
        )

    def check(
        self,
        *,
        context: CommunicationContext,
        decision: CommunicationDecision,
    ) -> GuardrailCheckResult:
        """
        Detect URLs in generated output and validate them.
        """

        started_at = perf_counter()
        violations: list[GuardrailViolation] = []

        validation_text = output_text_for_validation(
            decision.output
        )

        if validation_text:
            urls = self.URL_PATTERN.findall(validation_text)

            invalid_syntax_count = 0
            unreachable_count = 0

            trailing_url_punctuation: Final[str] = (
                ".,!?;:)]}"
            )

            for url in urls:
                url = url.rstrip(
                    trailing_url_punctuation
                )

                if not self._has_valid_syntax(url):
                    invalid_syntax_count += 1
                    continue

                if self._reachability_check_enabled:
                    if not self._is_reachable(url):
                        unreachable_count += 1

            if invalid_syntax_count > 0:
                violations.append(
                    GuardrailViolation(
                        code="URL_INVALID_SYNTAX",
                        category=GuardrailCategory.OUTPUT_SCHEMA,
                        severity=GuardrailSeverity.ERROR,
                        message=(
                            "Generated communication contains a "
                            "malformed URL."
                        ),
                        field="output",
                        safe_metadata={
                            "invalid_count": invalid_syntax_count,
                        },
                    )
                )

            if unreachable_count > 0:
                violations.append(
                    GuardrailViolation(
                        code="URL_UNREACHABLE",
                        category=GuardrailCategory.OUTPUT_SCHEMA,
                        severity=GuardrailSeverity.WARNING,
                        message=(
                            "Generated communication contains a "
                            "URL that could not be reached."
                        ),
                        field="output",
                        safe_metadata={
                            "unreachable_count": unreachable_count,
                        },
                    )
                )

        latency_ms = (
            perf_counter() - started_at
        ) * 1000

        return GuardrailCheckResult(
            checker_name=self.checker_name,
            passed=not violations,
            violations=tuple(violations),
            latency_ms=latency_ms,
        )

    @classmethod
    def _has_valid_syntax(cls, url: str) -> bool:
        """
        Validate URL syntax without making a network call.
        """

        try:
            parsed = urlparse(url)
        except ValueError:
            return False

        return (
            parsed.scheme.lower() in cls.ALLOWED_SCHEMES
            and bool(parsed.netloc)
        )

    def _is_reachable(self, url: str) -> bool:
        """
        Check reachability via the injected provider.

        Provider errors are treated as "not reachable" rather
        than raised, so a flaky network check degrades to a
        WARNING-level violation instead of crashing the pipeline.
        """

        provider = self._reachability_provider

        if provider is None:
            return True

        try:
            result = provider.check_reachable(url=url)
        except URLReachabilityProviderError:
            return False

        return result.reachable


# ==========================================================
# E.164 Phone Format Validation
# ==========================================================


class PhoneFormatValidator:
    """
    Validate that phone-like numbers in generated communication
    use strict E.164 formatting.

    Distinct from PIIOutputDetector: that checker answers
    "does this output contain a phone number at all?"

    This checker answers:
    "if a phone number appears, is it correctly formatted
    as E.164?"
    """

    checker_name: Final[str] = "phone_format_validator"

    # Strict E.164:
    # '+' followed by 1-15 digits,
    # with the first digit after '+' being 1-9.
    E164_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"^\+[1-9]\d{1,14}$"
    )

    # Finds phone-like numeric candidates.
    PHONE_CANDIDATE_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"(?<![A-Za-z0-9])"
        r"(?:\+?\d|\(\d)"
        r"[\d().\-\s]{7,}"
        r"\d"
        r"(?![A-Za-z0-9])"
    )

    def check(
        self,
        *,
        context: CommunicationContext,
        decision: CommunicationDecision,
    ) -> GuardrailCheckResult:
        """
        Scan generated output for phone-like numbers and flag
        any that are not valid E.164.
        """

        started_at = perf_counter()
        violations: list[GuardrailViolation] = []

        validation_text = output_text_for_validation(
            decision.output
        )

        if validation_text:
            invalid_count = (
                self._count_non_e164_candidates(
                    validation_text
                )
            )

            if invalid_count > 0:
                violations.append(
                    GuardrailViolation(
                        code="PHONE_NUMBER_NOT_E164",
                        category=GuardrailCategory.OUTPUT_SCHEMA,
                        severity=GuardrailSeverity.ERROR,
                        message=(
                            "Generated communication contains a "
                            "phone number that is not formatted "
                            "as E.164."
                        ),
                        field="output",
                        safe_metadata={
                            "invalid_count": invalid_count
                        },
                    )
                )

        latency_ms = (
            perf_counter() - started_at
        ) * 1000

        return GuardrailCheckResult(
            checker_name=self.checker_name,
            passed=not violations,
            violations=tuple(violations),
            latency_ms=latency_ms,
        )

    @classmethod
    def _count_non_e164_candidates(
        cls,
        value: str,
    ) -> int:
        """
        Count phone-like candidates that are not valid E.164.

        A candidate is skipped when:

        - It is not actually phone-shaped.
        - It follows a known non-phone identifier label such as
          JOB, TICKET, CASE, ORDER, or REF.

        Formatted phone numbers are considered invalid because
        E.164 requires a '+' followed by digits only.
        """

        count = 0

        for match in cls.PHONE_CANDIDATE_PATTERN.finditer(
            value
        ):
            candidate = match.group(0).strip()

            digit_count = sum(
                character.isdigit()
                for character in candidate
            )

            # Ignore things that are too short or too long to be
            # plausible phone numbers.
            if not 7 <= digit_count <= 15:
                continue

            # Ignore numbers that belong to non-phone
            # identifiers such as JOB-1234567890.
            if cls._has_identifier_prefix(
                value=value,
                match_start=match.start(),
            ):
                continue

            # Project-specific NANP validation:
            #
            # +1 must contain +1 followed by exactly
            # 10 additional digits.
            #
            # Valid:
            #   +14155552671
            #
            # Invalid:
            #   +1415555267
            if candidate.startswith("+1"):
                if digit_count != 11:
                    count += 1
                    continue

            # Strict E.164.
            if cls.E164_PATTERN.fullmatch(candidate):
                continue

            count += 1

        return count

    @staticmethod
    def _has_identifier_prefix(
        *,
        value: str,
        match_start: int,
    ) -> bool:
        """
        Return True when a numeric candidate follows a known
        non-phone identifier label.

        Examples:
            JOB-1234567890
            TICKET-1234567890
            CASE-1234567890
            ORDER-1234567890
            REF-1234567890
        """

        prefix = value[
            max(0, match_start - 20):match_start
        ]

        identifier_prefix_pattern = re.compile(
            r"(?:job|ticket|case|order|reference|ref)"
            r"[\s_:#-]*$",
            re.IGNORECASE,
        )

        return (
            identifier_prefix_pattern.search(prefix)
            is not None
        )

    @classmethod
    def is_valid_e164(cls, value: str) -> bool:
        """
        Return True when the supplied string is strict E.164.

        Exposed as a small reusable utility for callers outside
        the guardrail pipeline.
        """

        return (
            cls.E164_PATTERN.fullmatch(
                value.strip()
            )
            is not None
        )


# ==========================================================
# Quality Scoring
# ==========================================================


class QualityValidator:
    """
    Score generated communication for readability, completeness,
    and tone, and optionally fail the pipeline below a threshold.
    """

    checker_name: Final[str] = "quality_validator"

    DEFAULT_MINIMUM_PASSING_SCORE: Final[int] = 60

    PLACEHOLDER_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\{\{[A-Za-z][A-Za-z0-9_]*\}\}"
    )

    UNFILLED_PLACEHOLDER_PATTERN: Final[
        re.Pattern[str]
    ] = re.compile(
        r"\{\{\s*\}\}|\{[A-Za-z0-9_]+\}"
    )

    IDEAL_MAX_AVG_SENTENCE_WORDS: Final[int] = 20

    IDEAL_MAX_AVG_WORD_LENGTH: Final[float] = 6.5

    MIN_COMPLETE_MESSAGE_LENGTH: Final[int] = 10

    def __init__(
        self,
        *,
        minimum_passing_score: int = (
            DEFAULT_MINIMUM_PASSING_SCORE
        ),
        tone_validator: ToneValidator | None = None,
    ) -> None:
        """
        Parameters
        ----------
        minimum_passing_score
            Score below which check() emits a violation.

        tone_validator
            Injectable ToneValidator instance.
        """

        if not 0 <= minimum_passing_score <= 100:
            raise ValueError(
                "minimum_passing_score must be between 0 and 100."
            )

        self._minimum_passing_score = (
            minimum_passing_score
        )

        self._tone_validator = (
            tone_validator or ToneValidator()
        )

    def check(
        self,
        *,
        context: CommunicationContext,
        decision: CommunicationDecision,
    ) -> GuardrailCheckResult:
        """
        Compute the quality score and fail only when it is below
        the configured minimum.
        """

        started_at = perf_counter()
        violations: list[GuardrailViolation] = []

        quality_score = self.score(
            context=context,
            decision=decision,
        )

        if quality_score < self._minimum_passing_score:
            violations.append(
                GuardrailViolation(
                    code="MESSAGE_QUALITY_BELOW_THRESHOLD",
                    category=GuardrailCategory.OUTPUT_SCHEMA,
                    severity=GuardrailSeverity.WARNING,
                    message=(
                        "Generated communication quality score "
                        "is below the configured minimum."
                    ),
                    field="output",
                    safe_metadata={
                        "quality_score": quality_score,
                        "minimum_passing_score": (
                            self._minimum_passing_score
                        ),
                    },
                )
            )

        latency_ms = (
            perf_counter() - started_at
        ) * 1000

        return GuardrailCheckResult(
            checker_name=self.checker_name,
            passed=not violations,
            violations=tuple(violations),
            latency_ms=latency_ms,
        )

    def score(
        self,
        *,
        context: CommunicationContext,
        decision: CommunicationDecision,
    ) -> int:
        """
        Return the 0-100 quality score unconditionally.

        Never raises for empty/degenerate text.
        """

        validation_text = output_text_for_validation(
            decision.output
        )

        if (
            not validation_text
            or not validation_text.strip()
        ):
            return 0

        readability_score = (
            self._readability_score(validation_text)
        )

        completeness_score = (
            self._completeness_score(validation_text)
        )

        tone_score = self._tone_score(
            context=context,
            decision=decision,
        )

        combined = (
            (readability_score * 0.35)
            + (completeness_score * 0.35)
            + (tone_score * 0.30)
        )

        return max(
            0,
            min(100, round(combined)),
        )

    @classmethod
    def _readability_score(
        cls,
        text: str,
    ) -> int:
        """
        Score plain-language readability from 0-100.
        """

        cleaned = cls.PLACEHOLDER_PATTERN.sub(
            " ",
            text,
        )

        sentences = [
            sentence.strip()
            for sentence in re.split(
                r"[.!?]+",
                cleaned,
            )
            if sentence.strip()
        ]

        if not sentences:
            return 0

        words = cleaned.split()

        if not words:# pragma: no cover
            return 0

        avg_sentence_words = (
            len(words) / len(sentences)
        )

        avg_word_length = (
            sum(len(word) for word in words)
            / len(words)
        )

        sentence_penalty = max(
            0.0,
            avg_sentence_words
            - cls.IDEAL_MAX_AVG_SENTENCE_WORDS,
        )

        word_penalty = max(
            0.0,
            avg_word_length
            - cls.IDEAL_MAX_AVG_WORD_LENGTH,
        )

        score = (
            100
            - (sentence_penalty * 2)
            - (word_penalty * 8)
        )

        return max(
            0,
            min(100, round(score)),
        )

    @classmethod
    def _completeness_score(
        cls,
        text: str,
    ) -> int:
        """
        Score whether the message reads as complete, from 0-100.

        Very short messages receive a score of 40.

        Longer messages are penalized for:
        - unfilled placeholders
        - missing terminal punctuation
        """

        stripped = text.strip()

        if not stripped:
            return 0

        # Test requirement:
        #
        # "Hi" -> 40
        #
        # We use a fixed score for trivial messages rather than
        # additionally applying the punctuation penalty.
        if len(stripped) < cls.MIN_COMPLETE_MESSAGE_LENGTH:
            return 40

        score = 100

        if cls.UNFILLED_PLACEHOLDER_PATTERN.search(
            stripped
        ):
            score -= 40

        if stripped[-1] not in ".!?":
            score -= 10

        return max(
            0,
            min(100, score),
        )

    def _tone_score(
        self,
        *,
        context: CommunicationContext,
        decision: CommunicationDecision,
    ) -> int:
        """
        Derive a tone component by reusing ToneValidator.
        """

        tone_result = self._tone_validator.check(
            context=context,
            decision=decision,
        )

        if tone_result.passed:
            return 100

        penalty = (
            30 * len(tone_result.violations)
        )

        return max(
            0,
            100 - penalty,
        )


# ==========================================================
# MessageValidator Facade
# ==========================================================


class MessageValidationResult(BaseModel):
    """
    Combined result returned by MessageValidator.

    Wraps GuardrailPipelineResult and adds the quality score.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        frozen=True,
    )

    pipeline_result: GuardrailPipelineResult = Field(
        ...,
        description=(
            "Result of running the full guardrail pipeline, "
            "including URL, phone, and quality checkers."
        ),
    )

    quality_score: int = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "0-100 quality score, always present regardless "
            "of whether the pipeline passed."
        ),
    )

    @property
    def passed(self) -> bool:
        """
        Return True only when the pipeline result allows use.
        """

        return self.pipeline_result.passed

    @property
    def requires_fallback(self) -> bool:
        """
        Return True when a Jinja2 fallback is required.
        """

        return self.pipeline_result.requires_fallback


class MessageValidator:
    """
    Facade that runs the complete message-validation suite.

    Existing guardrails:
        - Channel
        - Length
        - Placeholder integrity
        - PII
        - Profanity
        - Brand safety
        - Tone

    New guardrails:
        - URL
        - Phone format
        - Quality
    """

    DEFAULT_QUALITY_MINIMUM_PASSING_SCORE: Final[int] = (
        QualityValidator.DEFAULT_MINIMUM_PASSING_SCORE
    )

    def __init__(
        self,
        *,
        pipeline: GuardrailPipeline | None = None,
        quality_validator: QualityValidator | None = None,
    ) -> None:
        """
        Parameters
        ----------
        pipeline
            Optional pre-built GuardrailPipeline.

        quality_validator
            Optional QualityValidator instance used to compute
            the always-present numeric score.
        """

        self._quality_validator = (
            quality_validator or QualityValidator()
        )

        self._pipeline = (
            pipeline
            or self.default_pipeline(
                quality_validator=self._quality_validator
            )
        )

    @staticmethod
    def default_pipeline(
        *,
        quality_validator: QualityValidator | None = None,
        fail_fast: bool = False,
        performance_budget_ms: float = (
            GuardrailPipeline.DEFAULT_PERFORMANCE_BUDGET_MS
        ),
    ) -> GuardrailPipeline:
        """
        Build the default guardrail pipeline.
        """

        quality_validator = (
            quality_validator or QualityValidator()
        )

        return GuardrailPipeline(
            checkers=(
                ChannelValidator(),
                LengthValidator(),
                PlaceholderIntegrityValidator(),
                PIIOutputDetector(),
                ProfanityValidator(),
                BrandSafetyValidator(),
                ToneValidator(),
                URLValidator(),
                PhoneFormatValidator(),
                quality_validator,
            ),
            fail_fast=fail_fast,
            performance_budget_ms=performance_budget_ms,
        )

    def validate(
        self,
        *,
        context: CommunicationContext,
        decision: CommunicationDecision,
    ) -> MessageValidationResult:
        """
        Run the complete validation suite and return the
        combined result.
        """

        pipeline_result = self._pipeline.run(
            context=context,
            decision=decision,
        )

        quality_score = self._quality_validator.score(
            context=context,
            decision=decision,
        )

        return MessageValidationResult(
            pipeline_result=pipeline_result,
            quality_score=quality_score,
        )