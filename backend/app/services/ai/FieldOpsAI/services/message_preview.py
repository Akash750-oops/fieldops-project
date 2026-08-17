"""
Message preview and approval workflow.

This module generates customer-facing message previews without sending them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.enterprise_audit import audit_log, AuditAction


@dataclass
class ChannelPreview:
    """Preview of a message for one communication channel."""

    channel: str
    subject: Optional[str]
    body: str
    character_count: int
    character_limit: Optional[int] = None

    @property
    def within_limit(self) -> bool:
        """Return True when the message is within its channel limit."""
        if self.character_limit is None:
            return True

        return self.character_count <= self.character_limit


@dataclass
class PreviewResult:
    """Result returned by the message preview workflow."""

    preview_id: str
    template_key: str
    channels: list[ChannelPreview]
    requires_approval: bool
    approval_reason: Optional[str] = None
    original_messages: dict[str, str] = field(default_factory=dict)
    edited_messages: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def sms(self) -> Optional[ChannelPreview]:
        """Return the SMS preview when available."""
        return next(
            (
                channel
                for channel in self.channels
                if channel.channel == "sms"
            ),
            None,
        )

    @property
    def email(self) -> Optional[ChannelPreview]:
        """Return the email preview when available."""
        return next(
            (
                channel
                for channel in self.channels
                if channel.channel == "email"
            ),
            None,
        )


@dataclass
class ApprovalResult:
    """Result of approving a message preview."""

    preview_id: str
    approved: bool
    approved_by: str
    approved_at: datetime
    original_messages: dict[str, str]
    edited_messages: dict[str, str]


@dataclass
class AuditEntry:
    """
    Audit information returned by the preview workflow.

    The persistent audit record is stored in enterprise_audit_logs.
    """

    preview_id: str
    action: str
    actor_id: str
    timestamp: datetime
    original_messages: dict[str, str]
    edited_messages: dict[str, str]


class MessagePreview:
    """
    Handles message preview, character counting, approval requirements,
    editing and audit information.

    IMPORTANT:
    This class does NOT send SMS/email messages.
    """

    SMS_CHARACTER_LIMIT = 160

    def __init__(
        self,
        communication_service,
        db: Session,
        tenant_id: str,
    ) -> None:
        self._communication_service = communication_service
        self._db = db
        self._tenant_id = str(tenant_id)

        self._previews: dict[str, PreviewResult] = {}

    def preview(
        self,
        context: Any,
        template_key: str,
        priority: Optional[str] = None,
        first_time_template: bool = False,
    ) -> PreviewResult:
        """
        Generate SMS and email previews.

        No SMS or email is sent.
        """

        if not template_key or not template_key.strip():
            raise ValueError("template_key is required")

        channels: list[ChannelPreview] = []
        original_messages: dict[str, str] = {}

        # ======================================================
        # Generate SMS preview
        # ======================================================

        sms_context = context.model_copy(
            update={"channel": "SMS"}
        )

        sms_result = self._communication_service.generate(
            context=sms_context,
        )

        sms_decision = sms_result.decision
        sms_output = sms_decision.output

        if sms_output.channel != "SMS":
            raise ValueError(
                f"Expected SMS output, got {sms_output.channel}"
            )

        sms_body = sms_output.text

        channels.append(
            ChannelPreview(
                channel="sms",
                subject=None,
                body=sms_body,
                character_count=len(sms_body),
                character_limit=self.SMS_CHARACTER_LIMIT,
            )
        )

        original_messages["sms"] = sms_body

        # ======================================================
        # Generate EMAIL preview
        # ======================================================

        email_context = context.model_copy(
            update={"channel": "EMAIL"}
        )

        email_result = self._communication_service.generate(
            context=email_context,
        )

        email_decision = email_result.decision
        email_output = email_decision.output

        if email_output.channel != "EMAIL":
            raise ValueError(
                f"Expected EMAIL output, got {email_output.channel}"
            )

        email_body = email_output.text_body

        channels.append(
            ChannelPreview(
                channel="email",
                subject=email_output.subject,
                body=email_body,
                character_count=len(email_body),
                character_limit=None,
            )
        )

        original_messages["email"] = email_body

        # ======================================================
        # Determine approval requirement
        # ======================================================

        requires_approval, approval_reason = (
            self.requires_approval(
                priority=priority,
                first_time_template=first_time_template,
                template_key=template_key,
            )
        )

        # ======================================================
        # Store preview
        # ======================================================

        preview_id = self._create_preview_id()

        result = PreviewResult(
            preview_id=preview_id,
            template_key=template_key,
            channels=channels,
            requires_approval=requires_approval,
            approval_reason=approval_reason,
            original_messages=original_messages.copy(),
            edited_messages=original_messages.copy(),
        )

        self._previews[preview_id] = result

        return result

    def requires_approval(
        self,
        *,
        priority: Optional[str],
        first_time_template: bool,
        template_key: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Determine whether operator approval is required.

        Approval is required when:

        1. Priority is HIGH or URGENT.
        2. The template is being used for the first time.
        """

        normalized_priority = (
            priority.strip().upper()
            if isinstance(priority, str)
            else None
        )

        if normalized_priority in {"HIGH", "URGENT"}:
            return (
                True,
                "HIGH priority message requires approval",
            )

        if first_time_template:
            return (
                True,
                f"First-time template '{template_key}' requires approval",
            )

        return False, None

    def edit(
        self,
        preview_id: str,
        edited_messages: dict[str, str],
    ) -> PreviewResult:
        """
        Edit an existing preview.

        The edited content is stored in the preview but is NOT sent.
        """

        result = self._get_preview(preview_id)

        if not edited_messages:
            raise ValueError(
                "edited_messages cannot be empty"
            )

        for channel, message in edited_messages.items():
            if channel not in {"sms", "email"}:
                raise ValueError(
                    f"Unsupported channel: {channel}"
                )

            if not isinstance(message, str):
                raise ValueError(
                    f"Edited {channel} message must be a string"
                )

            if not message.strip():
                raise ValueError(
                    f"Edited {channel} message cannot be empty"
                )

            if (
                channel == "sms"
                and len(message) > self.SMS_CHARACTER_LIMIT
            ):
                raise ValueError(
                    "SMS message exceeds the 160 character limit"
                )

        result.edited_messages.update(
            edited_messages
        )

        for channel_preview in result.channels:
            if channel_preview.channel in edited_messages:
                edited_body = edited_messages[
                    channel_preview.channel
                ]

                channel_preview.body = edited_body
                channel_preview.character_count = len(
                    edited_body
                )

        return result

    def approve(
        self,
        preview_id: str,
        actor_id: str,
        *,
        user_email: Optional[str] = None,
        role: Optional[str] = None,
        correlation_id: Optional[str] = None,
        request: Any = None,
    ) -> ApprovalResult:
        """
        Approve a preview and persist an enterprise audit record.

        Approval itself does NOT send the message.
        """

        if not actor_id or not actor_id.strip():
            raise ValueError("actor_id is required")

        result = self._get_preview(preview_id)

        # ------------------------------------------------------
        # Approval must actually be required.
        # ------------------------------------------------------

        if not result.requires_approval:
            raise ValueError(
                "This preview does not require approval"
            )

        approved_at = datetime.now(timezone.utc)

        original_messages = (
            result.original_messages.copy()
        )

        edited_messages = (
            result.edited_messages.copy()
        )

        # ------------------------------------------------------
        # Persistent enterprise audit record
        # ------------------------------------------------------

        audit_entry = audit_log(
            self._db,
            action=AuditAction.MESSAGE_PREVIEW_APPROVED,
            tenant_id=self._tenant_id,
            user_id=str(actor_id),
            user_email=user_email,
            role=role,
            entity_type="message_preview",
            entity_id=preview_id,
            old_value={
                "sms": original_messages.get("sms"),
                "email": original_messages.get("email"),
            },
            new_value={
                "sms": edited_messages.get("sms"),
                "email": edited_messages.get("email"),
            },
            details={
                "template_key": result.template_key,
                "approval_reason": result.approval_reason,
                "created_at": result.created_at.isoformat(),
                "approved_at": approved_at.isoformat(),
                "sms_character_count": (
                    len(edited_messages["sms"])
                    if "sms" in edited_messages
                    else None
                ),
                "email_character_count": (
                    len(edited_messages["email"])
                    if "email" in edited_messages
                    else None
                ),
            },
            severity="INFO",
            correlation_id=correlation_id,
            request=request,
        )

        # ------------------------------------------------------
        # Persist the audit record.
        # ------------------------------------------------------

        self._db.commit()
        self._db.refresh(audit_entry)

        return ApprovalResult(
            preview_id=preview_id,
            approved=True,
            approved_by=str(actor_id),
            approved_at=approved_at,
            original_messages=original_messages,
            edited_messages=edited_messages,
        )

    def get_preview(
        self,
        preview_id: str,
    ) -> PreviewResult:
        """Return an existing preview."""

        return self._get_preview(preview_id)

    def side_by_side(
        self,
        preview_id: str,
    ) -> dict[str, ChannelPreview]:
        """
        Return the SMS and email previews keyed by channel,
        for side-by-side display.
        """

        result = self._get_preview(preview_id)

        return {
            channel.channel: channel
            for channel in result.channels
        }

    def _get_preview(
        self,
        preview_id: str,
    ) -> PreviewResult:
        try:
            return self._previews[preview_id]
        except KeyError as exc:
            raise ValueError(
                f"Preview '{preview_id}' was not found"
            ) from exc

    @staticmethod
    def _create_preview_id() -> str:
        """Create a unique preview ID."""
        return str(uuid.uuid4())