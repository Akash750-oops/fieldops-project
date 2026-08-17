"""
Message preview and approval API routes.

These endpoints generate customer-facing SMS and email previews
without sending them.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ..database import get_db
from ..services.ai.FieldOpsAI.services.communication_service import (
    CommunicationService,
)
from ..services.ai.FieldOpsAI.services.message_preview import (
    MessagePreview,
    PreviewResult,
)
from ..services.ai.FieldOpsAI.schemas.communication import (
    CommunicationContext,
)


router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
)


# ==========================================================
# Request Models
# ==========================================================


class PreviewRequest(BaseModel):
    """
    Request to generate a message preview.

    priority and first_time_template belong to the preview
    workflow, not CommunicationContext.
    """

    context: CommunicationContext
    template_key: str = Field(min_length=1)
    priority: str | None = None
    first_time_template: bool = False


class EditRequest(BaseModel):
    """Operator edits to an existing message preview."""

    edited_messages: dict[str, str]


# ==========================================================
# In-memory workflow registry
# ==========================================================

_preview_services: dict[str, MessagePreview] = {}


# ==========================================================
# Helpers
# ==========================================================


def _build_message_preview(
    *,
    db: Session,
    tenant_id: str,
) -> MessagePreview:
    """
    Create a message preview workflow for a tenant.
    """

    communication_service = CommunicationService(
        db=db,
        tenant_id=tenant_id,
    )

    return MessagePreview(
        communication_service=communication_service,
        db=db,
        tenant_id=tenant_id,
    )


def _store_preview_service(
    preview_service: MessagePreview,
) -> None:
    """
    Store the workflow service by preview ID.

    MessagePreview currently keeps previews in memory, so the
    service instance must remain available for edit/approval.
    """

    previews = getattr(
        preview_service,
        "_previews",
        {},
    )

    for preview_id in previews:
        _preview_services[preview_id] = preview_service


def _get_preview_service(
    *,
    preview_id: str,
    tenant_id: str,
) -> MessagePreview:
    """
    Retrieve a preview service and ensure that it belongs
    to the authenticated tenant.
    """

    preview_service = _preview_services.get(preview_id)

    if preview_service is None:
        raise HTTPException(
            status_code=404,
            detail="Message preview was not found.",
        )

    stored_tenant_id = getattr(
        preview_service,
        "_tenant_id",
        None,
    )

    if stored_tenant_id is not None:
        if str(stored_tenant_id) != str(tenant_id):
            raise HTTPException(
                status_code=404,
                detail="Message preview was not found.",
            )

    return preview_service


def _serialize_preview(
    result: PreviewResult,
) -> dict[str, Any]:
    """
    Convert a PreviewResult into an API response.
    """

    return {
        "preview_id": result.preview_id,
        "template_key": result.template_key,
        "requires_approval": result.requires_approval,
        "approval_reason": result.approval_reason,
        "created_at": result.created_at,
        "sms": (
            {
                "channel": result.sms.channel,
                "subject": result.sms.subject,
                "body": result.sms.body,
                "character_count": result.sms.character_count,
                "character_limit": result.sms.character_limit,
                "within_limit": result.sms.within_limit,
            }
            if result.sms
            else None
        ),
        "email": (
            {
                "channel": result.email.channel,
                "subject": result.email.subject,
                "body": result.email.body,
                "character_count": result.email.character_count,
                "character_limit": result.email.character_limit,
                "within_limit": result.email.within_limit,
            }
            if result.email
            else None
        ),
    }


# ==========================================================
# Preview
# ==========================================================


@router.post("/preview")
def create_message_preview(
    payload: PreviewRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate SMS and email previews.

    No SMS or email is sent.
    """

    preview_service = _build_message_preview(
        db=db,
        tenant_id=str(current_user.tenant_id),
    )

    try:
        result = preview_service.preview(
            context=payload.context,
            template_key=payload.template_key,
            priority=payload.priority,
            first_time_template=payload.first_time_template,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    _store_preview_service(preview_service)

    return _serialize_preview(result)


# ==========================================================
# Edit
# ==========================================================


@router.patch("/{preview_id}")
def edit_message_preview(
    preview_id: str,
    payload: EditRequest,
    current_user=Depends(get_current_user),
):
    """
    Save operator edits to an existing preview.

    Editing does not send the message.
    """

    preview_service = _get_preview_service(
        preview_id=preview_id,
        tenant_id=str(current_user.tenant_id),
    )

    try:
        result = preview_service.edit(
            preview_id=preview_id,
            edited_messages=payload.edited_messages,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return _serialize_preview(result)


# ==========================================================
# Approval
# ==========================================================


@router.post("/{preview_id}/approve")
def approve_message_preview(
    preview_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    """
    Approve an existing message preview.

    Approval creates a persistent audit entry but does NOT
    send the SMS or email.

    The approval actor always comes from the authenticated
    user rather than from the request body.
    """

    preview_service = _get_preview_service(
        preview_id=preview_id,
        tenant_id=str(current_user.tenant_id),
    )

    try:
        result = preview_service.approve(
            preview_id=preview_id,
            actor_id=str(current_user.user_id),
            user_email=getattr(
                current_user,
                "email",
                None,
            ),
            role=getattr(
                current_user,
                "role",
                None,
            ),
            request=request,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        "preview_id": result.preview_id,
        "approved": result.approved,
        "approved_by": result.approved_by,
        "approved_at": result.approved_at,
        "original_messages": result.original_messages,
        "edited_messages": result.edited_messages,
    }