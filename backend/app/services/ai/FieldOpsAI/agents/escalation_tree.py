"""
escalation_tree.py

Deterministic escalation decision tree for FieldOps Commander.

The decision tree determines:
- whether escalation is required
- escalation priority
- escalation target
- SLA
- acknowledgement message

The tree does not:
- call an LLM
- send notifications
- update jobs
- modify technicians
- persist directly to the database
"""

from __future__ import annotations

import re
import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ==========================================================
# Enums
# ==========================================================


class EscalationLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EscalationTarget(str, Enum):
    NONE = "NONE"
    SENTIMENT_AGENT = "SENTIMENT_AGENT"
    DISPATCH_AGENT = "DISPATCH_AGENT"
    HUMAN_OPERATOR = "HUMAN_OPERATOR"


# ==========================================================
# Context
# ==========================================================


class EscalationContext(BaseModel):
    """
    Input required by the escalation decision tree.
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
    )

    sentiment: str | None = None

    sentiment_urgency: EscalationLevel | None = None

    sentiment_requires_human: bool = False

    intent: str | None = None

    customer_is_vip: bool = False

    messages_last_hour: int = Field(
        default=0,
        ge=0,
    )

    urgent_job: bool = False

    job_id: str | None = None

    customer_id: str | None = None


# ==========================================================
# Decision
# ==========================================================


class EscalationDecision(BaseModel):
    """
    Result returned by the escalation decision tree.
    """

    should_escalate: bool

    level: EscalationLevel

    target: EscalationTarget

    triggers: list[str]

    reason: str

    sla_minutes: int | None

    sla_deadline: datetime | None

    acknowledgement: str | None


class EscalationAuditEntry(BaseModel):
    """Immutable audit payload emitted when an escalation is selected."""

    occurred_at: datetime
    customer_id: str | None
    job_id: str | None
    level: EscalationLevel
    target: EscalationTarget
    triggers: list[str]
    reason: str
    sla_minutes: int
    sla_deadline: datetime


# ==========================================================
# Decision Tree
# ==========================================================


class EscalationDecisionTree:
    """
    Deterministic business-rule engine for communication
    escalation.
    """

    SLA_MINUTES = {
        EscalationLevel.CRITICAL: 5,
        EscalationLevel.HIGH: 15,
        EscalationLevel.MEDIUM: 60,
        EscalationLevel.LOW: 240,
    }

    HUMAN_REQUEST_PATTERNS = (
        r"\bhuman\b",
        r"\breal person\b",
        r"\boperator\b",
        r"\bspeak to someone\b",
        r"\btalk to someone\b",
        r"\bagent\b",
    )

    COMPLAINT_PATTERNS = (
        r"\bcomplaint\b",
        r"\bcomplain\b",
        r"\bunhappy\b",
        r"\bterrible service\b",
        r"\bpoor service\b",
        r"\bdisappointed\b",
    )

    def __init__(
        self,
        *,
        redis_client: Any | None = None,
        customer_history_provider: Callable[[str], Mapping[str, Any]] | None = None,
        audit_logger: Callable[[EscalationAuditEntry], None] | None = None,
        sla_timer: Callable[[EscalationDecision], None] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.redis_client = redis_client
        self.customer_history_provider = customer_history_provider
        self.audit_logger = audit_logger
        self.sla_timer = sla_timer
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def evaluate(
        self,
        context: EscalationContext,
    ) -> EscalationDecision:
        """
        Evaluate all escalation rules and return one decision.
        """

        context = self._enrich_context(context)
        triggers: list[str] = []

        # --------------------------------------------------
        # 1. Explicit human request
        # --------------------------------------------------

        if self._explicit_human_request(context.message):
            triggers.append("EXPLICIT_HUMAN_REQUEST")

        # --------------------------------------------------
        # 2. Negative sentiment
        # --------------------------------------------------

        if (
            context.sentiment
            and context.sentiment.strip().upper() == "NEGATIVE"
        ):
            triggers.append("NEGATIVE_SENTIMENT")

        # --------------------------------------------------
        # 3. Complaint intent
        # --------------------------------------------------

        if (
            context.intent
            and context.intent.strip().upper() == "COMPLAINT"
        ):
            triggers.append("COMPLAINT_INTENT")
        elif self._complaint_detected(context.message):
            triggers.append("COMPLAINT_CONTENT")

        # --------------------------------------------------
        # 4. VIP customer
        # --------------------------------------------------

        if context.customer_is_vip:
            triggers.append("VIP_CUSTOMER")

        # --------------------------------------------------
        # 5. Repeated messages
        # --------------------------------------------------

        repeated_message_threshold = self._repeated_message_threshold()
        if context.messages_last_hour >= repeated_message_threshold:
            triggers.append("REPEATED_MESSAGES")

        # --------------------------------------------------
        # 6. Urgent job
        # --------------------------------------------------

        if context.urgent_job:
            triggers.append("URGENT_JOB")

        # --------------------------------------------------
        # 7. AI explicitly recommends human
        # --------------------------------------------------

        if context.sentiment_requires_human:
            triggers.append("SENTIMENT_REQUIRES_HUMAN")

        if context.sentiment_urgency == EscalationLevel.CRITICAL:
            triggers.append("CRITICAL_SENTIMENT_URGENCY")

        # --------------------------------------------------
        # No escalation
        # --------------------------------------------------

        if not triggers:
            return EscalationDecision(
                should_escalate=False,
                level=EscalationLevel.LOW,
                target=EscalationTarget.NONE,
                triggers=[],
                reason="No escalation rule was triggered.",
                sla_minutes=None,
                sla_deadline=None,
                acknowledgement=None,
            )

        level = self._calculate_priority(
            context=context,
            triggers=triggers,
        )

        target = self._route(
            context=context,
            triggers=triggers,
            level=level,
        )

        sla_minutes = self.SLA_MINUTES[level]

        deadline = self.clock() + timedelta(minutes=sla_minutes)

        acknowledgement = self._generate_ack(
            level=level,
            sla_minutes=sla_minutes,
        )

        decision = EscalationDecision(
            should_escalate=True,
            level=level,
            target=target,
            triggers=triggers,
            reason=self._build_reason(triggers),
            sla_minutes=sla_minutes,
            sla_deadline=deadline,
            acknowledgement=acknowledgement,
        )

        self._emit_audit(context, decision)
        if self.sla_timer is not None:
            self.sla_timer(decision)

        return decision

    def _enrich_context(
        self,
        context: EscalationContext,
    ) -> EscalationContext:
        """Load optional customer history without requiring a database call."""
        if self.customer_history_provider is None or not context.customer_id:
            return context

        try:
            history = self.customer_history_provider(context.customer_id)
        except Exception:
            logger.warning(
                "Customer history lookup failed during escalation evaluation.",
                exc_info=True,
            )
            return context
        if not history:
            return context

        updates: dict[str, Any] = {}
        if context.messages_last_hour == 0:
            updates["messages_last_hour"] = history.get(
                "messages_last_hour", 0
            )
        if not context.customer_is_vip:
            updates["customer_is_vip"] = bool(
                history.get("customer_is_vip", False)
            )
        return context.model_copy(update=updates)

    def _emit_audit(
        self,
        context: EscalationContext,
        decision: EscalationDecision,
    ) -> None:
        entry = EscalationAuditEntry(
            occurred_at=self.clock(),
            customer_id=context.customer_id,
            job_id=context.job_id,
            level=decision.level,
            target=decision.target,
            triggers=decision.triggers,
            reason=decision.reason,
            sla_minutes=decision.sla_minutes or 0,
            sla_deadline=decision.sla_deadline or self.clock(),
        )

        if self.audit_logger is not None:
            self.audit_logger(entry)
        else:
            logger.info(
                "communication_escalated",
                extra=entry.model_dump(mode="json"),
            )

    def _cached_rule(self, name: str, default: Any) -> Any:
        """Read an optional JSON rule override; Redis failures fail open."""
        if self.redis_client is None:
            return default
        try:
            raw = self.redis_client.get("fieldops:escalation:rules")
            rules = json.loads(raw) if raw else {}
            return rules.get(name, default)
        except Exception:
            return default

    def _repeated_message_threshold(self) -> int:
        configured = self._cached_rule("messages_last_hour_threshold", 3)
        try:
            return max(1, int(configured))
        except (TypeError, ValueError):
            return 3

    # ======================================================
    # Trigger Detection
    # ======================================================

    def _explicit_human_request(
        self,
        message: str,
    ) -> bool:
        normalized = message.lower()

        return any(
            re.search(pattern, normalized)
            for pattern in self.HUMAN_REQUEST_PATTERNS
        )

    def _complaint_detected(
        self,
        message: str,
    ) -> bool:
        normalized = message.lower()

        return any(
            re.search(pattern, normalized)
            for pattern in self.COMPLAINT_PATTERNS
        )

    # ======================================================
    # Priority
    # ======================================================

    def _calculate_priority(
        self,
        *,
        context: EscalationContext,
        triggers: Sequence[str],
    ) -> EscalationLevel:

        # Explicit human request + urgent/critical situation
        if (
            "EXPLICIT_HUMAN_REQUEST" in triggers
            and (
                context.urgent_job
                or context.sentiment_urgency
                == EscalationLevel.CRITICAL
            )
        ):
            return EscalationLevel.CRITICAL

        # AI / business logic already says critical
        if (
            context.sentiment_urgency
            == EscalationLevel.CRITICAL
        ):
            return EscalationLevel.CRITICAL

        # Urgent jobs need immediate dispatch attention
        if "URGENT_JOB" in triggers:
            return EscalationLevel.HIGH

        # Multiple serious escalation conditions
        if len(triggers) >= 3:
            return EscalationLevel.HIGH

        # Human request / complaint / VIP
        if any(
            trigger in triggers
            for trigger in (
                "EXPLICIT_HUMAN_REQUEST",
                "COMPLAINT_INTENT",
                "COMPLAINT_CONTENT",
                "VIP_CUSTOMER",
                "SENTIMENT_REQUIRES_HUMAN",
            )
        ):
            return EscalationLevel.HIGH

        # Negative sentiment / repeated messages
        if any(
            trigger in triggers
            for trigger in (
                "NEGATIVE_SENTIMENT",
                "REPEATED_MESSAGES",
            )
        ):
            return EscalationLevel.MEDIUM

        return EscalationLevel.LOW

    # ======================================================
    # Routing
    # ======================================================

    def _route(
        self,
        *,
        context: EscalationContext,
        triggers: Sequence[str],
        level: EscalationLevel,
    ) -> EscalationTarget:

        # Explicit human request always wins.
        if "EXPLICIT_HUMAN_REQUEST" in triggers:
            return EscalationTarget.HUMAN_OPERATOR

        # Complex / high-priority customer issue.
        if any(
            trigger in triggers
            for trigger in (
                "COMPLAINT_INTENT",
                "COMPLAINT_CONTENT",
                "VIP_CUSTOMER",
                "SENTIMENT_REQUIRES_HUMAN",
            )
        ):
            return EscalationTarget.HUMAN_OPERATOR

        # Job operational issue.
        if "URGENT_JOB" in triggers:
            return EscalationTarget.DISPATCH_AGENT

        # Sentiment-specific issue.
        if "NEGATIVE_SENTIMENT" in triggers:
            return EscalationTarget.SENTIMENT_AGENT

        # Repeated messages indicate possible unresolved
        # communication issue.
        if "REPEATED_MESSAGES" in triggers:
            return EscalationTarget.HUMAN_OPERATOR

        return EscalationTarget.HUMAN_OPERATOR

    # ======================================================
    # Response
    # ======================================================

    def _generate_ack(
        self,
        *,
        level: EscalationLevel,
        sla_minutes: int,
    ) -> str:

        if sla_minutes < 60:
            eta = f"{sla_minutes} minutes"
        else:
            hours = sla_minutes // 60
            unit = "hour" if hours == 1 else "hours"
            eta = f"{hours} {unit}"

        return (
            "Thank you for contacting us. "
            "Your request has been escalated to our support team. "
            f"A response is expected within {eta}."
        )

    # ======================================================
    # Reason
    # ======================================================

    def _build_reason(
        self,
        triggers: Sequence[str],
    ) -> str:

        readable = [
            trigger.replace("_", " ").lower()
            for trigger in triggers
        ]

        return (
            "Escalation triggered by: "
            + ", ".join(readable)
            + "."
        )