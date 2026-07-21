from __future__ import annotations

import re
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.prompt_admin_authorization import (
    PromptAdminPrincipal,
    require_prompt_admin,
)
from app.redis_client import get_redis_client
from app.services.ai.FieldOpsAI.schemas.prompt_template import (
    AgentType,
    PromptChannel,
    PromptLanguage,
    PromptTemplateCreate,
    PromptTemplateLookupResponse,
    PromptTemplateResponse,
    PromptTemplateUpdate,
)
from app.services.ai.FieldOpsAI.services.managed_prompt_template_registry import (
    ConflictError,
    ManagedPromptTemplateRegistry,
    NotFoundError,
    RegistryServiceError,
    TemplateValidationServiceError,
)


router = APIRouter(
    prefix="/admin/prompts",
    tags=["Admin Prompts"],
)


# ==========================================================
# Validation helpers
# ==========================================================


def normalize_status(
    value: Optional[str],
) -> Optional[str]:
    """
    Normalize a prompt status into lowercase snake_case.

    Examples:
        ASSIGNED -> assigned
        en_route -> en_route

    Blank or unsafe status values are rejected.
    """

    if value is None:
        return None

    normalized = value.strip().lower()

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Status cannot be blank.",
        )

    if not re.fullmatch(
        r"[a-z0-9_]+",
        normalized,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Status must use lowercase snake_case.",
        )

    return normalized


# ==========================================================
# Dependencies
# ==========================================================


def get_registry(
    principal: PromptAdminPrincipal = Depends(
        require_prompt_admin
    ),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> ManagedPromptTemplateRegistry:
    """
    Build a tenant-scoped registry for the authenticated actor.
    """

    return ManagedPromptTemplateRegistry(
        db=db,
        tenant_id=principal.tenant_id,
        actor_id=principal.actor_id,
        redis_client=redis_client,
    )


# ==========================================================
# Create
# ==========================================================


@router.post(
    "",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_prompt(
    payload: PromptTemplateCreate,
    registry: ManagedPromptTemplateRegistry = Depends(
        get_registry
    ),
) -> PromptTemplateResponse:
    try:
        return registry.create(payload)

    except ConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An active template with this "
                "configuration already exists."
            ),
        ) from None

    except TemplateValidationServiceError:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Template validation failed.",
        ) from None

    except RegistryServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prompt registry unavailable.",
        ) from None


# ==========================================================
# List
# ==========================================================


@router.get(
    "",
    response_model=list[PromptTemplateResponse],
)
def list_prompts(
    agent_type: Optional[AgentType] = Query(
        default=None
    ),
    channel: Optional[PromptChannel] = Query(
        default=None
    ),
    language: Optional[PromptLanguage] = Query(
        default=None
    ),
    prompt_status: Optional[str] = Query(
        default=None,
        alias="status",
    ),
    is_active: Optional[bool] = Query(
        default=None
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    registry: ManagedPromptTemplateRegistry = Depends(
        get_registry
    ),
) -> list[PromptTemplateResponse]:
    normalized_status = normalize_status(
        prompt_status
    )

    filters = {
        "agent_type": (
            agent_type.value
            if agent_type is not None
            else None
        ),
        "channel": (
            channel.value
            if channel is not None
            else None
        ),
        "language": (
            language.value
            if language is not None
            else None
        ),
        "status": normalized_status,
        "is_active": is_active,
        "limit": limit,
        "offset": offset,
    }

    filtered_values = {
        key: value
        for key, value in filters.items()
        if value is not None
    }

    try:
        return registry.list(
            **filtered_values
        )

    except RegistryServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prompt registry unavailable.",
        ) from None


# ==========================================================
# Lookup
# ==========================================================


@router.get(
    "/lookup",
    response_model=PromptTemplateLookupResponse,
)
def lookup_prompt(
    agent_type: AgentType = Query(...),
    channel: PromptChannel = Query(...),
    language: PromptLanguage = Query(...),
    prompt_status: str = Query(
        ...,
        alias="status",
        min_length=1,
    ),
    registry: ManagedPromptTemplateRegistry = Depends(
        get_registry
    ),
) -> PromptTemplateLookupResponse:
    normalized_status = normalize_status(
        prompt_status
    )

    if normalized_status is None:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Status is required.",
        )

    try:
        return registry.find(
            agent_type=agent_type.value,
            channel=channel.value,
            language=language.value,
            status=normalized_status,
        )

    except TemplateValidationServiceError:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Prompt lookup validation failed.",
        ) from None

    except RegistryServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prompt registry unavailable.",
        ) from None


# ==========================================================
# Get by ID
# ==========================================================


@router.get(
    "/{template_id}",
    response_model=PromptTemplateResponse,
)
def get_prompt(
    template_id: int = Path(
        ...,
        ge=1,
    ),
    registry: ManagedPromptTemplateRegistry = Depends(
        get_registry
    ),
) -> PromptTemplateResponse:
    try:
        return registry.get(
            template_id
        )

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        ) from None

    except RegistryServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prompt registry unavailable.",
        ) from None


# ==========================================================
# Update
# ==========================================================


@router.patch(
    "/{template_id}",
    response_model=PromptTemplateResponse,
)
def update_prompt(
    payload: PromptTemplateUpdate,
    template_id: int = Path(
        ...,
        ge=1,
    ),
    registry: ManagedPromptTemplateRegistry = Depends(
        get_registry
    ),
) -> PromptTemplateResponse:
    try:
        return registry.update(
            template_id=template_id,
            payload=payload,
        )

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        ) from None

    except ConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The requested update conflicts "
                "with another template."
            ),
        ) from None

    except TemplateValidationServiceError:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Template validation failed.",
        ) from None

    except RegistryServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prompt registry unavailable.",
        ) from None


# ==========================================================
# Soft delete
# ==========================================================


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_prompt(
    template_id: int = Path(
        ...,
        ge=1,
    ),
    registry: ManagedPromptTemplateRegistry = Depends(
        get_registry
    ),
) -> Response:
    try:
        registry.delete(
            template_id
        )

        return Response(
            status_code=status.HTTP_204_NO_CONTENT
        )

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        ) from None

    except RegistryServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prompt registry unavailable.",
        ) from None