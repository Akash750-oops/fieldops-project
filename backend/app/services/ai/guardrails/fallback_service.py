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

from jinja2 import (
    StrictUndefined,
    TemplateError,
    meta,
)
from jinja2.sandbox import SandboxedEnvironment
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import NotificationTemplate
from app.services.default_template import (
    NOTIFICATION_TYPES,
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

    # Safe values prevent None/null/undefined from entering
    # recipient-facing communication.
    SAFE_OPTIONAL_DEFAULTS: Final[
        dict[str, str]
    ] = {
        "customer_name": "Customer",
        "technician_name": "Your technician",
        "job_title": "your service request",
        "eta": "not yet available",
        "appointment_time": "the scheduled time",
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

        self._text_environment = (
            self._build_environment(
                autoescape=False
            )
        )

        self._html_environment = (
            self._build_environment(
                autoescape=True
            )
        )

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
            decision = self._try_build_decision(
                context=context,
                title_template=(
                    template_row.title_template
                ),
                body_template=(
                    template_row.body_template
                ),
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

        builtin = self._get_builtin_template(
            context=context
        )

        if builtin is not None:
            decision = self._try_build_decision(
                context=context,
                title_template=builtin["title"],
                body_template=builtin["body"],
            )

            if decision is not None:
                return GuardrailFallbackResult(
                    decision=decision,
                    source=(
                        FallbackTemplateSource.BUILTIN
                    ),
                    requested_locale=context.locale,
                    resolved_locale="en",
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

        for locale in self._locale_candidates(
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

    # ------------------------------------------------------

    @staticmethod
    def _locale_candidates(
        locale: str,
    ) -> tuple[str, ...]:
        """
        Return exact locale, base language, and English.

        Examples
        --------
        en-US:
            en-US, en

        ta-IN:
            ta-IN, ta, en
        """

        candidates: list[str] = [
            locale,
        ]

        if "-" in locale:
            candidates.append(
                locale.split(
                    "-",
                    1,
                )[0]
            )

        candidates.append(
            "en"
        )

        # Remove duplicate values while preserving order.
        return tuple(
            dict.fromkeys(
                candidates
            )
        )

    # ======================================================
    # Built-in Template Selection
    # ======================================================

    @staticmethod
    def _get_builtin_template(
        *,
        context: CommunicationContext,
    ) -> dict[
        str,
        str | None,
    ] | None:
        """
        Return an approved built-in event template.

        Built-in templates come from:

        app/services/default_template.py
        """

        event_template = NOTIFICATION_TYPES.get(
            context.notification_type
        )

        if event_template is None:
            return None

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
            return None

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
        }

    # ======================================================
    # Decision Rendering
    # ======================================================

    def _try_build_decision(
        self,
        *,
        context: CommunicationContext,
        title_template: str | None,
        body_template: str,
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

            message = self._render_string(
                template_source=body_template,
                render_context=render_context,
                html=(
                    context.channel
                    == "EMAIL"
                ),
            )

            rendered_title: str | None = None

            if title_template is not None:
                rendered_title = self._render_string(
                    template_source=(
                        title_template
                    ),
                    render_context=render_context,
                    html=False,
                )

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

        except (
            TemplateError,
            TypeError,
            ValueError,
        ):
            return None

    # ======================================================
    # Secure Jinja Rendering
    # ======================================================

    def _render_string(
        self,
        *,
        template_source: str,
        render_context: dict[str, str],
        html: bool,
    ) -> str:
        """
        Render one sandboxed Jinja2 template string.
        """

        if not isinstance(
            template_source,
            str,
        ):
            raise TypeError(
                "Fallback template source must be text."
            )

        environment = (
            self._html_environment
            if html
            else self._text_environment
        )

        parsed_template = environment.parse(
            template_source
        )

        variables = (
            meta.find_undeclared_variables(
                parsed_template
            )
        )

        unsupported_variables = (
            variables
            - self.ALLOWED_TEMPLATE_VARIABLES
        )

        if unsupported_variables:
            raise ValueError(
                "Fallback template contains unsupported "
                "variables."
            )

        template = environment.from_string(
            template_source
        )

        rendered = str(
            template.render(
                **render_context
            )
        ).strip()

        # Text channels should not contain unexpected line
        # breaks or repeated whitespace.
        if not html:
            rendered = re.sub(
                r"\s+",
                " ",
                rendered,
            ).strip()

        if not rendered:
            raise ValueError(
                "Fallback template rendered empty content."
            )

        if self.INVALID_OUTPUT_TOKEN_PATTERN.search(
            rendered
        ):
            raise ValueError(
                "Fallback template rendered an invalid "
                "optional value."
            )

        return rendered

    # ======================================================
    # Safe Template Context
    # ======================================================

    def _build_render_context(
        self,
        context: CommunicationContext,
    ) -> dict[str, str]:
        """
        Build a null-safe and allow-listed rendering context.

        additional_context and correlation_id are deliberately
        excluded.
        """

        context_data = context.model_dump(
            mode="python"
        )

        rendered_context: dict[
            str,
            str,
        ] = {}

        for key in self.ALLOWED_TEMPLATE_VARIABLES:
            value = context_data.get(
                key
            )

            if value is None:
                value = (
                    self.SAFE_OPTIONAL_DEFAULTS.get(
                        key,
                        "",
                    )
                )

            rendered_context[key] = str(
                value
            )

        return rendered_context

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

    # ======================================================
    # Jinja Environment
    # ======================================================

    @staticmethod
    def _build_environment(
        *,
        autoescape: bool,
    ) -> SandboxedEnvironment:
        """
        Create a restricted Jinja2 environment.

        SandboxedEnvironment prevents templates from accessing
        unsafe Python internals.

        StrictUndefined rejects missing template variables.

        Email values are HTML escaped.
        """

        environment = SandboxedEnvironment(
            undefined=StrictUndefined,
            autoescape=autoescape,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Templates do not need Jinja globals such as:
        #
        # range
        # cycler
        # joiner
        # namespace
        #
        # Removing them reduces the available template surface.
        environment.globals.clear()

        return environment