"""
fallback_service.py

Approved Jinja2 fallback rendering for FieldOps communication.

The service is used when:

- The external AI provider is unavailable
- The provider response cannot be parsed
- Generated communication fails the guardrail pipeline
- A required AI safety dependency fails closed

Rendering order
---------------
1. Active database template for the requested locale
2. Active database template for the base/English locale
3. Approved built-in FieldOps event template
4. Approved channel-specific emergency template

The service never:

- Calls an external AI provider
- Restores real PII values
- Sends a notification
- Commits or rolls back a database transaction
- Uses free-form additional_context in a template
"""

from __future__ import annotations

import re

from enum import StrEnum
from typing import Final

from app.services.ai.FieldOpsAI.services.prompt_variable_injector import (
    PromptVariableInjector
)
from app.services.ai.FieldOpsAI.schemas.prompt_variable import PromptVariableDefinition
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models import NotificationTemplate
from app.services.ai.FieldOpsAI.services.prompt_locale_service import locale_candidates
from app.services.default_template import (
    LOCALIZED_NOTIFICATION_TYPES,
)
from app.services.ai.FieldOpsAI.schemas.communication import (
    CommunicationContext,
    CommunicationDecision,
)


# ==========================================================
# Fallback Result Contracts
# ==========================================================


class FallbackTemplateSource(StrEnum):
    """
    Origin of the approved fallback template.
    """

    DATABASE = "DATABASE"
    BUILTIN = "BUILTIN"
    EMERGENCY = "EMERGENCY"


class GuardrailFallbackResult(BaseModel):
    """
    Safe result returned after fallback rendering.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    decision: CommunicationDecision

    source: FallbackTemplateSource

    requested_locale: str = Field(
        min_length=2,
        max_length=10,
    )

    resolved_locale: str = Field(
        min_length=2,
        max_length=10,
    )

    template_id: int | None = None

    template_version: int | None = None


class GuardrailFallbackError(RuntimeError):
    """
    Raised only when no approved safe fallback can be built.
    """


# ==========================================================
# Fallback Service
# ==========================================================


class GuardrailFallbackService:
    """
    Render deterministic, approved fallback communication.
    """

    # ------------------------------------------------------
    # Allowed template variables
    # ------------------------------------------------------

    ALLOWED_TEMPLATE_VARIABLES: Final[
        frozenset[str]
    ] = frozenset(
        {
            "job_id",
            "notification_type",
            "recipient_type",
            "channel",
            "locale",
            "customer_name",
            "technician_name",
            "job_status",
            "job_title",
            "eta",
            "appointment_time",
            "sentiment",
        }
    )

    SAFE_OPTIONAL_DEFAULTS: Final[
        dict[str, dict[str, str]]
    ] = {
        "en": {
            "customer_name": "Customer",
            "technician_name": "Your technician",
            "job_title": "your service request",
            "eta": "not yet available",
            "appointment_time": "the scheduled time",
        },
        "es": {
            "customer_name": "Cliente",
            "technician_name": "Su técnico",
            "job_title": "su solicitud de servicio",
            "eta": "aún no disponible",
            "appointment_time": "la hora programada",
        },
        "ta": {
            "customer_name": "வாடிக்கையாளர்",
            "technician_name": "உங்கள் தொழில்நுட்பவியலாளர்",
            "job_title": "உங்கள் சேவை கோரிக்கை",
            "eta": "இன்னும் கிடைக்கவில்லை",
            "appointment_time": "திட்டமிடப்பட்ட நேரம்",
        },
        "hi": {
            "customer_name": "ग्राहक",
            "technician_name": "आपके तकनीशियन",
            "job_title": "आपका सेवा अनुरोध",
            "eta": "अभी उपलब्ध नहीं है",
            "appointment_time": "निर्धारित समय",
        }
    }

    # ------------------------------------------------------
    # Final emergency fallback
    # ------------------------------------------------------

    EMERGENCY_TEMPLATES: Final[
        dict[
            str,
            dict[str, str | None],
        ]
    ] = {
        "SMS": {
            "title": None,
            "body": (
                "Your FieldOps service request has an update. "
                "Please check the app."
            ),
        },

        "EMAIL": {
            "title": "FieldOps service update",
            "body": (
                "<p>"
                "Your FieldOps service request has an update. "
                "Please check the portal for details."
                "</p>"
            ),
        },

        "PUSH": {
            "title": "FieldOps update",
            "body": (
                "Your service request has a new update."
            ),
        },

        "IN_APP": {
            "title": "FieldOps update",
            "body": (
                "Your service request has a new update."
            ),
        },
    }

    INVALID_OUTPUT_TOKEN_PATTERN: Final[
        re.Pattern[str]
    ] = re.compile(
        r"\b(?:none|null|undefined)\b",
        re.IGNORECASE,
    )

    SMS_MAX_LENGTH: Final[int] = 160

    EMAIL_SUBJECT_MAX_LENGTH: Final[int] = 78

    PUSH_TITLE_MAX_LENGTH: Final[int] = 50

    # ------------------------------------------------------

    def __init__(
        self,
        *,
        db: Session,
    ) -> None:
        """
        Initialize the fallback service.

        Parameters
        ----------
        db
            Existing SQLAlchemy session used to retrieve
            approved NotificationTemplate records.
        """

        self._db = db

    # ------------------------------------------------------

    def render(
        self,
        *,
        context: CommunicationContext,
    ) -> GuardrailFallbackResult:
        """
        Render the safest available fallback.

        Selection order:

        1. Database template
        2. Built-in event template
        3. Emergency template
        """

        (
            template_row,
            resolved_locale,
        ) = self._find_database_template(
            context=context
        )

        # --------------------------------------------------
        # 1. Approved database template
        # --------------------------------------------------

        if template_row is not None:
            if template_row.variables:
                db_vars = []
                for v in template_row.variables:
                    if isinstance(v, dict):
                        db_vars.append(PromptVariableDefinition(**v))
                    elif isinstance(v, str):
                        db_vars.append(PromptVariableDefinition(name=v))
            else:
                db_vars = None

            decision = self._try_build_decision(
                context=context,
                title_template=(
                    template_row.title_template
                ),
                body_template=(
                    template_row.body_template
                ),
                variables=db_vars,
                resolved_locale=resolved_locale,
            )

            if decision is not None:
                return GuardrailFallbackResult(
                    decision=decision,
                    source=(
                        FallbackTemplateSource.DATABASE
                    ),
                    requested_locale=context.locale,
                    resolved_locale=resolved_locale,
                    template_id=template_row.id,
                    template_version=(
                        template_row.version
                    ),
                )

        # --------------------------------------------------
        # 2. Approved built-in event template
        # --------------------------------------------------

        builtin_result = self._get_builtin_template(
            context=context
        )

        if builtin_result is not None:
            builtin, builtin_locale = builtin_result
            decision = self._try_build_decision(
                context=context,
                title_template=builtin["title"],
                body_template=builtin["body"],
                resolved_locale=builtin_locale,
            )

            if decision is not None:
                return GuardrailFallbackResult(
                    decision=decision,
                    source=(
                        FallbackTemplateSource.BUILTIN
                    ),
                    requested_locale=context.locale,
                    resolved_locale=builtin_locale,
                )

        # --------------------------------------------------
        # 3. Approved emergency template
        # --------------------------------------------------

        emergency = self.EMERGENCY_TEMPLATES.get(
            context.channel
        )

        if emergency is None:
            raise GuardrailFallbackError(
                "No approved fallback is configured for "
                "the communication channel."
            )

        decision = self._try_build_decision(
            context=context,
            title_template=emergency["title"],
            body_template=emergency["body"],
            resolved_locale="en",
        )

        if decision is None:
            raise GuardrailFallbackError(
                "Approved emergency fallback could not be "
                "rendered."
            )

        return GuardrailFallbackResult(
            decision=decision,
            source=(
                FallbackTemplateSource.EMERGENCY
            ),
            requested_locale=context.locale,
            resolved_locale="en",
        )

    # ======================================================
    # Database Template Lookup
    # ======================================================

    def _find_database_template(
        self,
        *,
        context: CommunicationContext,
    ) -> tuple[
        NotificationTemplate | None,
        str,
    ]:
        """
        Find the first active locale-compatible template.

        Example locale order:

        en-US
            ↓
        en
        """

        for locale in locale_candidates(
            context.locale
        ):
            try:
                row = (
                    self._db.query(
                        NotificationTemplate
                    )
                    .filter(
                        NotificationTemplate.type
                        == context.notification_type,

                        NotificationTemplate.channel
                        == context.channel.lower(),

                        NotificationTemplate.locale
                        == locale,

                        NotificationTemplate.is_active
                        .is_(True),

                        NotificationTemplate.tenant_id
                        == "**platform**",

                        NotificationTemplate.agent_type
                        == "CommsAgent",

                        NotificationTemplate.is_deleted
                        .is_(False),
                    )
                    .order_by(
                        NotificationTemplate.version.desc(),
                        NotificationTemplate.id.desc(),
                    )
                    .first()
                )

            except SQLAlchemyError:
                # A fallback must remain available even when
                # template database access fails.
                return None, "en"

            if row is not None:
                return row, locale

        return None, "en"

    # ======================================================
    # Built-in Template Selection
    # ======================================================

    @staticmethod
    def _get_builtin_template(
        *,
        context: CommunicationContext,
    ) -> tuple[
        dict[str, str | None],
        str
    ] | None:
        """
        Return an approved built-in event template.

        Built-in templates come from:

        app/services/default_template.py
        """
        
        candidates = locale_candidates(context.locale)
        
        for cand in candidates:
            catalog = LOCALIZED_NOTIFICATION_TYPES.get(cand)
            if catalog is None:
                continue
                
            event_template = catalog.get(
                context.notification_type
            )

            if event_template is None:
                continue

            body = event_template.get(
                context.channel.lower()
            )

            if (
                not isinstance(
                    body,
                    str,
                )
                or not body.strip()
            ):
                continue

            title: str | None = None

            if context.channel in {
                "EMAIL",
                "PUSH",
                "IN_APP",
            }:
                candidate_title = event_template.get(
                    "title"
                )

                if isinstance(
                    candidate_title,
                    str,
                ):
                    title = candidate_title

            return {
                "title": title,
                "body": body,
            }, cand
            
        return None

    # ======================================================
    # Decision Rendering
    # ======================================================

    def _try_build_decision(
        self,
        *,
        context: CommunicationContext,
        title_template: str | None,
        body_template: str,
        variables: list[PromptVariableDefinition] | None = None,
        resolved_locale: str = "en",
    ) -> CommunicationDecision | None:
        """
        Render and validate one fallback candidate.

        Invalid templates are rejected without exposing their
        content in an exception or log.
        """

        try:
            render_context = (
                self._build_render_context(
                    context
                )
            )

            injector = PromptVariableInjector()

            if variables is None:
                # Infer for built-in/emergency
                try:
                    paths = injector.infer_declarations(
                        body=body_template,
                        title=title_template
                    )
                except Exception:
                    paths = []
                    
                
                locale_defaults = self.SAFE_OPTIONAL_DEFAULTS.get(resolved_locale, self.SAFE_OPTIONAL_DEFAULTS["en"])
                variables = []
                for path in paths:
                    key = path.split('.')[0]
                    if key in self.ALLOWED_TEMPLATE_VARIABLES:
                        if key in locale_defaults:
                            variables.append(PromptVariableDefinition(
                                name=key,
                                required=False,
                                default=locale_defaults[key]
                            ))
                        else:
                            variables.append(PromptVariableDefinition(
                                name=key,
                                required=True
                            ))
            else:
                # For database templates, only use approved variables
                filtered_vars = []
                for v in variables:
                    key = v.name.split('.')[0]
                    if key not in self.ALLOWED_TEMPLATE_VARIABLES:
                        raise ValueError("Unapproved variable declaration")
                    filtered_vars.append(v)
                variables = filtered_vars

            result = injector.render(
                body=body_template,
                title=title_template,
                variables=variables,
                context=render_context,
                html=(context.channel == "EMAIL"),
            )

            message = result.rendered_body.strip()
            if context.channel != "EMAIL":
                message = re.sub(r"\s+", " ", message).strip()

            if not message or self.INVALID_OUTPUT_TOKEN_PATTERN.search(message):
                return None

            rendered_title: str | None = None
            if title_template is not None:
                rendered_title = result.rendered_title.strip() if result.rendered_title else ""
                rendered_title = re.sub(r"\s+", " ", rendered_title).strip()
                if not rendered_title or self.INVALID_OUTPUT_TOKEN_PATTERN.search(rendered_title):
                    return None

            # ----------------------------------------------
            # EMAIL
            # ----------------------------------------------

            if context.channel == "EMAIL":
                if rendered_title is None:
                    return None

                decision = CommunicationDecision(
                    channel="EMAIL",
                    title=None,
                    subject=rendered_title,
                    message=message,
                    tone="PROFESSIONAL",
                    confidence=1.0,
                )

            # ----------------------------------------------
            # PUSH
            # ----------------------------------------------

            elif context.channel == "PUSH":
                if rendered_title is None:
                    return None

                decision = CommunicationDecision(
                    channel="PUSH",
                    title=rendered_title,
                    subject=None,
                    message=message,
                    tone="PROFESSIONAL",
                    confidence=1.0,
                )

            # ----------------------------------------------
            # IN-APP
            # ----------------------------------------------

            elif context.channel == "IN_APP":
                decision = CommunicationDecision(
                    channel="IN_APP",
                    title=rendered_title,
                    subject=None,
                    message=message,
                    tone="PROFESSIONAL",
                    confidence=1.0,
                )

            # ----------------------------------------------
            # SMS
            # ----------------------------------------------

            else:
                decision = CommunicationDecision(
                    channel="SMS",
                    title=None,
                    subject=None,
                    message=message,
                    tone="PROFESSIONAL",
                    confidence=1.0,
                )

            if not self._within_channel_limits(
                decision
            ):
                return None

            return decision

        except Exception:
            return None

    # ======================================================
    # Safe Template Context
    # ======================================================

    def _build_render_context(
        self,
        context: CommunicationContext,
    ) -> dict[str, str]:
        """
        Build a null-safe and allow-listed rendering context.
        """
        return context.model_dump(mode="python")

    # ======================================================
    # Channel Limits
    # ======================================================

    @classmethod
    def _within_channel_limits(
        cls,
        decision: CommunicationDecision,
    ) -> bool:
        """
        Ensure the fallback itself respects hard channel limits.
        """

        if decision.channel == "SMS":
            return (
                len(
                    decision.message
                )
                <= cls.SMS_MAX_LENGTH
            )

        if decision.channel == "EMAIL":
            return (
                decision.subject is not None
                and len(
                    decision.subject
                )
                <= cls.EMAIL_SUBJECT_MAX_LENGTH
            )

        if decision.channel == "PUSH":
            return (
                decision.title is not None
                and len(
                    decision.title
                )
                <= cls.PUSH_TITLE_MAX_LENGTH
            )

        return True
