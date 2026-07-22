from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.prompt_admin_authorization import (
    PromptAdminPrincipal,
    require_prompt_admin,
)
from app.schemas import (
    TemplateVersionResponse,
    TemplateVersionHistoryResponse,
    TemplateRestoreRequest,
    TemplateRestoreResponse,
    TemplateCompareResponse,
)
from fastapi import Path
from app.services import template_version_service
from app.redis_client import get_redis_client
from app.services.ai.FieldOpsAI.services.managed_prompt_template_registry import ManagedPromptTemplateRegistry
from app.services.template_version_service import (
    TemplateNotFoundError,
    VersionNotFoundError,
    ConflictError as VersionConflictError,
    TemplateVersionError
)

router = APIRouter(
    prefix="/templates",
    tags=["Template Versioning (Legacy)"],
)

@router.get(
    "/{template_id}/versions",
    response_model=TemplateVersionHistoryResponse,
    summary="List all template versions",
    deprecated=True
)
def list_template_versions(
    template_id: int = Path(..., ge=1),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    principal: PromptAdminPrincipal = Depends(require_prompt_admin)
):
    try:
        versions = template_version_service.get_versions(
            db=db,
            template_id=template_id,
            tenant_id=principal.tenant_id,
            limit=limit,
            offset=offset
        )
        current = template_version_service.get_current_version(
            db=db,
            template_id=template_id,
            tenant_id=principal.tenant_id
        )
        return {
            "template_id": template_id,
            "current_version": current,
            "versions": versions,
        }
    except (TemplateNotFoundError, VersionNotFoundError):
        raise HTTPException(status_code=404, detail="Template or version not found or inaccessible")
    except Exception as e:
        raise HTTPException(status_code=503, detail="Safe persistence failure")


@router.get(
    "/{template_id}/versions/{version_number}",
    response_model=TemplateVersionResponse,
    summary="Get one template version",
    deprecated=True
)
def get_template_version(
    template_id: int = Path(..., ge=1),
    version_number: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    principal: PromptAdminPrincipal = Depends(require_prompt_admin)
):
    try:
        return template_version_service.get_version(
            db=db,
            template_id=template_id,
            version_number=version_number,
            tenant_id=principal.tenant_id
        )
    except (TemplateNotFoundError, VersionNotFoundError):
        raise HTTPException(status_code=404, detail="Template or version not found or inaccessible")
    except Exception as e:
        raise HTTPException(status_code=503, detail="Safe persistence failure")


@router.post(
    "/{template_id}/restore",
    response_model=TemplateRestoreResponse,
    summary="Restore an older template version",
    deprecated=True
)
def restore_template_version(
    payload: TemplateRestoreRequest,
    template_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    principal: PromptAdminPrincipal = Depends(require_prompt_admin),
    redis_client = Depends(get_redis_client)
):
    try:
        res = template_version_service.restore_version(
            db=db,
            template_id=template_id,
            version_number=payload.version_number,
            actor_id=principal.actor_id,
            tenant_id=principal.tenant_id,
        )
        db.commit()

        # Invalidate cache
        registry = ManagedPromptTemplateRegistry(
            db=db,
            tenant_id=principal.tenant_id,
            actor_id=principal.actor_id,
            redis_client=redis_client,
        )
        registry._invalidate_cache()

        return res
    except (TemplateNotFoundError, VersionNotFoundError):
        db.rollback()
        raise HTTPException(status_code=404, detail="Template or version not found or inaccessible")
    except VersionConflictError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Version conflict or invalid state")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=503, detail="Safe persistence failure")


@router.get(
    "/{template_id}/compare",
    response_model=TemplateCompareResponse,
    summary="Compare two template versions",
    deprecated=True
)
def compare_template_versions(
    old_version: int = Query(..., ge=1),
    new_version: int = Query(..., ge=1),
    template_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    principal: PromptAdminPrincipal = Depends(require_prompt_admin)
):
    try:
        return template_version_service.compare_versions(
            db=db,
            template_id=template_id,
            old_version=old_version,
            new_version=new_version,
            tenant_id=principal.tenant_id
        )
    except (TemplateNotFoundError, VersionNotFoundError):
        raise HTTPException(status_code=404, detail="Template or version not found or inaccessible")
    except Exception as e:
        raise HTTPException(status_code=503, detail="Safe persistence failure")


@router.delete(
    "/{template_id}/versions/{version_number}",
    summary="Delete a template version",
    deprecated=True,
)
def delete_template_version(
    version_number: int = Path(..., ge=1),
    template_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    principal: PromptAdminPrincipal = Depends(
        require_prompt_admin
    ),
    redis_client=Depends(get_redis_client),
):
    try:
        result = template_version_service.delete_version(
            db=db,
            template_id=template_id,
            version_number=version_number,
            actor_id=principal.actor_id,
            tenant_id=principal.tenant_id,
        )

        db.commit()

        registry = ManagedPromptTemplateRegistry(
            db=db,
            tenant_id=principal.tenant_id,
            actor_id=principal.actor_id,
            redis_client=redis_client,
        )
        registry._invalidate_cache()

        return result

    except (
        TemplateNotFoundError,
        VersionNotFoundError,
    ):
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail=(
                "Template or version not found "
                "or inaccessible"
            ),
        ) from None

    except VersionConflictError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Version conflict or invalid state",
        ) from None

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Safe persistence failure",
        ) from None