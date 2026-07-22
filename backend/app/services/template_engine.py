import os
import time
import jwt
from sqlalchemy.orm import Session
from app.models import NotificationTemplate, TemplateVersion
from app.services.ai.FieldOpsAI.schemas.prompt_template import PromptTemplateLookupResponse, PromptChannel
from app.services.ai.FieldOpsAI.services.prompt_variable_injector import PromptVariableInjector
from app.services.ai.FieldOpsAI.schemas.prompt_variable import PromptVariableDefinition
from app.services.ai.FieldOpsAI.services.prompt_locale_service import locale_candidates
from ..logger import logger


def sign_url(
    base_url: str,
    job_id: str,
    tech_id: str,
    action: str,
    expiry: int = 600,
) -> str:
    """
    Generate a signed action URL.

    Fail closed when the signing secret is missing.
    """

    secret = os.getenv(
        "JWT_SECRET"
    )

    if not secret:
        raise RuntimeError(
            "Action URL signing is unavailable."
        )

    payload = {
        "job_id": str(job_id),
        "tech_id": str(tech_id),
        "action": action,
        "exp": (
            int(time.time())
            + expiry
        ),
    }

    token = jwt.encode(
        payload,
        secret,
        algorithm="HS256",
    )

    separator = (
        "&"
        if "?" in base_url
        else "?"
    )

    return (
        f"{base_url}"
        f"{separator}"
        f"token={token}"
    )

def get_action_urls(
    job_id: str,
    tech_id: str,
) -> dict[str, str]:
    """
    Generate standard action URLs.

    Fail closed when the base URL is missing.
    """

    base_api_url = os.getenv(
        "BASE_API_URL"
    )

    if not base_api_url:
        raise RuntimeError(
            "Action URL base is unavailable."
        )

    base_api_url = (
        base_api_url.rstrip("/")
    )

    return {
        "accept": sign_url(
            (
                f"{base_api_url}/jobs/"
                f"{job_id}/accept"
            ),
            job_id,
            tech_id,
            "accept",
        ),
        "reject": sign_url(
            (
                f"{base_api_url}/jobs/"
                f"{job_id}/reject"
            ),
            job_id,
            tech_id,
            "reject",
        ),
        "reassign": sign_url(
            (
                f"{base_api_url}/jobs/"
                f"{job_id}/reassign"
            ),
            job_id,
            tech_id,
            "reassign",
        ),
    }
def render_notification(
    db: Session, 
    template_type: str, 
    channel: str, 
    context: dict,
    locale: str = "en"
) -> dict:
    """
    Fetch the active template and render it using Jinja2 with the provided context.
    Provides standard fallback if template is completely missing or crashes.
    """
    template = None
    for cand in locale_candidates(locale):
        template = db.query(NotificationTemplate).filter(
            NotificationTemplate.type == template_type,
            NotificationTemplate.channel == channel,
            NotificationTemplate.locale == cand,
            NotificationTemplate.is_active == True,
            NotificationTemplate.tenant_id == "**platform**",
            NotificationTemplate.agent_type == "CommsAgent",
            NotificationTemplate.is_deleted == False
        ).first()
        if template:
            break

    # Generic Fallback if still no template
    if not template:
        logger.warning(f"No active template found for {template_type}/{channel}/{locale}")
        return {
            "title": "New Notification",
            "body": "You have a new update. Please check the app."
        }

    render_context = context.copy()
    # Inject standard action URLs if job and tech IDs exist in context
    if "job" in render_context and "tech" in render_context:
        try:
            job_id = render_context["job"].get("id", render_context["job"].get("job_id"))
            tech_id = render_context["tech"].get("id", render_context["tech"].get("tech_id"))
            if job_id and tech_id:
                render_context["action_urls"] = get_action_urls(job_id, tech_id)
        except (
                AttributeError,
            RuntimeError,
        ):
            # Rendering continues safely without action URLs
            # when IDs or signing configuration are missing.
            pass

    try:
        injector = PromptVariableInjector()
        variables = template.variables if template.variables else []
        result = injector.render(
            body=template.body_template,
            variables=variables,
            context=render_context,
            title=template.title_template,
            html=(channel.lower() == "email")
        )
        return {
            "title": result.rendered_title,
            "body": result.rendered_body
        }
    except Exception as e:
        logger.error(f"Template rendering error for template_id={template.id}, version={template.version}: {type(e).__name__}")
        return {
            "title": "System Alert",
            "body": "A new assignment is available. Please open the app."
        }

def render_preview(title_template: str, body_template: str, context: dict, variables: list | None = None) -> dict:
    """Render a raw template string with mock context for the preview API."""
    injector = PromptVariableInjector()
    
    if variables is None:
        try:
            paths = injector.infer_declarations(body=body_template, title=title_template)
            variables = [{"name": p, "required": True} for p in paths]
        except Exception:
            variables = []

    result = injector.render(
        body=body_template,
        variables=variables,
        context=context,
        title=title_template,
        html=False
    )

    return {
        "title": result.rendered_title,
        "body": result.rendered_body
    }

def test_sign_url_fails_without_secret(
    monkeypatch,
):
    monkeypatch.delenv(
        "JWT_SECRET",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="signing is unavailable",
    ):
        sign_url(
            "https://example.test/action",
            "job-1",
            "tech-1",
            "accept",
        )

def test_action_urls_fail_without_base_url(
    monkeypatch,
):
    monkeypatch.setenv(
        "JWT_SECRET",
        "test-secret",
    )

    monkeypatch.delenv(
        "BASE_API_URL",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="base is unavailable",
    ):
        get_action_urls(
            "job-1",
            "tech-1",
        )