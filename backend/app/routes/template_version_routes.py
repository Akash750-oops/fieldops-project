from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    TemplateVersionCreate,
    TemplateVersionResponse,
    TemplateVersionHistoryResponse,
    TemplateRestoreRequest,
    TemplateRestoreResponse,
    TemplateCompareResponse,
)
from app.services import template_version_service

router = APIRouter(
    prefix="/templates",
    tags=["Template Versioning"],
)


@router.post(
    "/{template_id}/versions",
    response_model=TemplateVersionResponse,
    summary="Create a new template version",
)
def create_template_version(
    template_id: int,
    payload: TemplateVersionCreate,
    db: Session = Depends(get_db),
):
    return template_version_service.create_version(
        db=db,
        template_id=template_id,
        payload=payload,
    )


@router.get(
    "/{template_id}/versions",
    response_model=TemplateVersionHistoryResponse,
    summary="List all template versions",
)
def list_template_versions(
    template_id: int,
    db: Session = Depends(get_db),
):
    versions = template_version_service.get_versions(
        db=db,
        template_id=template_id,
    )

    current = versions[0].version_number if versions else 0

    return {
        "template_id": template_id,
        "current_version": current,
        "versions": versions,
    }


@router.get(
    "/{template_id}/versions/{version_number}",
    response_model=TemplateVersionResponse,
    summary="Get one template version",
)
def get_template_version(
    template_id: int,
    version_number: int,
    db: Session = Depends(get_db),
):
    return template_version_service.get_version(
        db=db,
        template_id=template_id,
        version_number=version_number,
    )


@router.post(
    "/{template_id}/restore",
    response_model=TemplateRestoreResponse,
    summary="Restore an older template version",
)
def restore_template_version(
    template_id: int,
    payload: TemplateRestoreRequest,
    db: Session = Depends(get_db),
):
    return template_version_service.restore_version(
        db=db,
        template_id=template_id,
        payload=payload,
    )


@router.get(
    "/{template_id}/compare",
    response_model=TemplateCompareResponse,
    summary="Compare two template versions",
)
def compare_template_versions(
    template_id: int,
    old_version: int,
    new_version: int,
    db: Session = Depends(get_db),
):
    return template_version_service.compare_versions(
        db=db,
        template_id=template_id,
        old_version=old_version,
        new_version=new_version,
    )


@router.delete(
    "/{template_id}/versions/{version_number}",
    summary="Delete a template version",
)
def delete_template_version(
    template_id: int,
    version_number: int,
    db: Session = Depends(get_db),
):
    return template_version_service.delete_version(
        db=db,
        template_id=template_id,
        version_number=version_number,
    )