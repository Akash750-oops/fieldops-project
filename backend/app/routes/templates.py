from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .dispatch import verify_jwt_token
from ..database import get_db
from ..models import NotificationTemplate,TemplateVersion
from ..schemas import TemplateCreate, TemplateResponse, TemplatePreviewRequest, TemplatePreviewResponse
from ..services.template_engine import render_preview

router = APIRouter(
    prefix="/templates",
    tags=["Templates"]
)

@router.post("", response_model=TemplateResponse)
async def create_template(
    payload: TemplateCreate,
    authorization: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    # Find existing active template of same type/channel/locale
    existing = db.query(NotificationTemplate).filter(
        NotificationTemplate.type == payload.type,
        NotificationTemplate.channel == payload.channel,
        NotificationTemplate.locale == payload.locale,
        NotificationTemplate.is_active == True
    ).first()

    new_version = 1

    if existing:
        new_version = existing.version + 1
        existing.is_active = False
        db.commit()

    # Create the active template
    new_template = NotificationTemplate(
        name=payload.name,
        type=payload.type,
        channel=payload.channel,
        locale=payload.locale,
        format=payload.format,
        title_template=payload.title_template,
        body_template=payload.body_template,
        version=new_version,
        is_active=True,
    )

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    # -------------------------------------------------
    # Automatically create a version history record
    # -------------------------------------------------

    version = TemplateVersion(
        template_id=new_template.id,
        version_number=new_version,
        title_template=new_template.title_template,
        body_template=new_template.body_template,
        created_by="system",
        change_summary="Initial version" if new_version == 1 else f"Version {new_version}",
        is_active=True,
    )

    db.add(version)
    db.commit()

    return new_template

@router.get("", response_model=list[TemplateResponse])
async def list_templates(
    db: Session = Depends(get_db),
    authorization: str = Depends(verify_jwt_token)
):
    # Only return active templates by default
    return db.query(NotificationTemplate).filter(NotificationTemplate.is_active == 1).all()

@router.post("/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    payload: TemplatePreviewRequest,
    authorization: str = Depends(verify_jwt_token)
):
    try:
        result = render_preview(
            title_template=payload.title_template,
            body_template=payload.body_template,
            context=payload.mock_context
        )
        return {
            "rendered_title": result["title"],
            "rendered_body": result["body"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Template render error: {str(e)}")
