from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from .dispatch import verify_jwt_token
from ..database import get_db
from ..models import NotificationTemplate,TemplateVersion
from ..schemas import TemplateCreate, TemplateResponse, TemplatePreviewRequest, TemplatePreviewResponse
from ..services.template_engine import render_preview
from ..services.ai.FieldOpsAI.schemas.prompt_template import _validate_jinja_variables

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
        NotificationTemplate.is_active == True,
        NotificationTemplate.tenant_id == "**platform**",
        NotificationTemplate.agent_type == "CommsAgent"
    ).first()

    new_version = 1

    if existing:
        new_version = existing.version + 1
        existing.is_active = False
        db.commit()

    # Derive variables automatically
    from jinja2 import Environment, meta
    env = Environment()
    ast = env.parse(payload.body_template)
    vars_set = meta.find_undeclared_variables(ast)
    if payload.title_template:
        ast_title = env.parse(payload.title_template)
        vars_set.update(meta.find_undeclared_variables(ast_title))
    variables = list(vars_set)

    # Create the active template
    new_template = NotificationTemplate(
        name=payload.name,
        type=payload.type,
        channel=payload.channel,
        locale=payload.locale,
        format=payload.format,
        title_template=payload.title_template,
        body_template=payload.body_template,
        variables=variables,
        version=new_version,
        is_active=True,
        tenant_id="**platform**",
        agent_type="CommsAgent"
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
    # Only return active platform CommsAgent templates by default
    return db.query(NotificationTemplate).filter(
        NotificationTemplate.is_active == True,
        NotificationTemplate.tenant_id == "**platform**",
        NotificationTemplate.agent_type == "CommsAgent"
    ).all()

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
    except Exception:
        raise HTTPException(status_code=400, detail="Template render failed.")
