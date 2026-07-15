from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import NotificationTemplate, TemplateVersion
from app.schemas import (
    TemplateVersionCreate,
    TemplateRestoreRequest,
)


def create_version(
    db: Session,
    template_id: int,
    payload: TemplateVersionCreate,
):
    """
    Create a new version of an existing notification template.
    """

    template = (
        db.query(NotificationTemplate)
        .filter(NotificationTemplate.id == template_id)
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=404,
            detail="Template not found",
        )

    latest = (
        db.query(TemplateVersion)
        .filter(TemplateVersion.template_id == template_id)
        .order_by(TemplateVersion.version_number.desc())
        .first()
    )

    next_version = 1
    if latest:
        next_version = latest.version_number + 1

    # Deactivate previous active version(s)
    (
        db.query(TemplateVersion)
        .filter(TemplateVersion.template_id == template_id)
        .update({"is_active": False})
    )

    version = TemplateVersion(
        template_id=template_id,
        version_number=next_version,
        title_template=payload.title_template,
        body_template=payload.body_template,
        created_by=payload.created_by,
        change_summary=payload.change_summary,
        is_active=True,
    )

    db.add(version)

    # Keep main template synchronized
    template.version = next_version
    template.title_template = payload.title_template
    template.body_template = payload.body_template

    db.commit()
    db.refresh(version)

    return version


def get_versions(
    db: Session,
    template_id: int,
):
    """
    Return all versions for a template.
    """

    template = (
        db.query(NotificationTemplate)
        .filter(NotificationTemplate.id == template_id)
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=404,
            detail="Template not found",
        )

    versions = (
        db.query(TemplateVersion)
        .filter(TemplateVersion.template_id == template_id)
        .order_by(TemplateVersion.version_number.desc())
        .all()
    )

    return versions


def get_version(
    db: Session,
    template_id: int,
    version_number: int,
):
    """
    Return a specific version.
    """

    version = (
        db.query(TemplateVersion)
        .filter(
            TemplateVersion.template_id == template_id,
            TemplateVersion.version_number == version_number,
        )
        .first()
    )

    if not version:
        raise HTTPException(
            status_code=404,
            detail="Version not found",
        )

    return version


def restore_version(
    db: Session,
    template_id: int,
    payload: TemplateRestoreRequest,
):
    """
    Restore an older version by creating a new active version.
    """

    template = (
        db.query(NotificationTemplate)
        .filter(NotificationTemplate.id == template_id)
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=404,
            detail="Template not found",
        )

    version = (
        db.query(TemplateVersion)
        .filter(
            TemplateVersion.template_id == template_id,
            TemplateVersion.version_number == payload.version_number,
        )
        .first()
    )

    if not version:
        raise HTTPException(
            status_code=404,
            detail="Requested version not found",
        )

    latest = (
        db.query(TemplateVersion)
        .filter(TemplateVersion.template_id == template_id)
        .order_by(TemplateVersion.version_number.desc())
        .first()
    )

    next_version = latest.version_number + 1

    # deactivate previous active versions
    (
        db.query(TemplateVersion)
        .filter(TemplateVersion.template_id == template_id)
        .update({"is_active": False})
    )

    restored = TemplateVersion(
        template_id=template_id,
        version_number=next_version,
        title_template=version.title_template,
        body_template=version.body_template,
        created_by=payload.restored_by,
        change_summary=f"Restored from version {payload.version_number}",
        is_active=True,
    )

    db.add(restored)

    template.version = next_version
    template.title_template = version.title_template
    template.body_template = version.body_template

    db.commit()
    db.refresh(restored)

    return {
        "template_id": template_id,
        "previous_version": payload.version_number,
        "restored_version": payload.version_number,
        "new_active_version": next_version,
        "restored_by": payload.restored_by,
        "restored_at": datetime.now(timezone.utc),
    }


def compare_versions(
    db: Session,
    template_id: int,
    old_version: int,
    new_version: int,
):
    """
    Compare two versions of a template.
    """

    old = (
        db.query(TemplateVersion)
        .filter(
            TemplateVersion.template_id == template_id,
            TemplateVersion.version_number == old_version,
        )
        .first()
    )

    if not old:
        raise HTTPException(
            status_code=404,
            detail=f"Version {old_version} not found",
        )

    new = (
        db.query(TemplateVersion)
        .filter(
            TemplateVersion.template_id == template_id,
            TemplateVersion.version_number == new_version,
        )
        .first()
    )

    if not new:
        raise HTTPException(
            status_code=404,
            detail=f"Version {new_version} not found",
        )

    return {
        "template_id": template_id,
        "old_version": old.version_number,
        "new_version": new.version_number,
        "old_title": old.title_template,
        "new_title": new.title_template,
        "old_body": old.body_template,
        "new_body": new.body_template,
    }


def delete_version(
    db: Session,
    template_id: int,
    version_number: int,
):
    """
    Delete a template version.

    Active versions cannot be deleted.
    """

    version = (
        db.query(TemplateVersion)
        .filter(
            TemplateVersion.template_id == template_id,
            TemplateVersion.version_number == version_number,
        )
        .first()
    )

    if not version:
        raise HTTPException(
            status_code=404,
            detail="Version not found",
        )

    if version.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete active version",
        )

    db.delete(version)
    db.commit()

    return {
        "message": "Version deleted successfully"
    }