import os
import time
import jwt
from jinja2 import Environment, BaseLoader, DebugUndefined
from sqlalchemy.orm import Session
from ..models import NotificationTemplate
from ..logger import logger

APP_SECRET = os.getenv('APP_SECRET', 'local_dummy_secret_do_not_use_in_prod')
BASE_API_URL = os.getenv('BASE_API_URL', 'https://api.fieldops.io/v1')

# We use DebugUndefined so missing variables don't crash the renderer, 
# they just render empty or we can catch them. We'll use a custom lenient undefined.
from jinja2 import Undefined

class LenientUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        # Return empty string instead of failing
        return ""
    
    __add__ = __radd__ = __mul__ = __rmul__ = __div__ = __rdiv__ = \
        __truediv__ = __rtruediv__ = __floordiv__ = __rfloordiv__ = \
        __mod__ = __rmod__ = __pos__ = __neg__ = __call__ = \
        __getattr__ = __getitem__ = __iter__ = __str__ = __repr__ = \
        _fail_with_undefined_error

# Initialize Jinja2 Environment
jinja_env = Environment(undefined=LenientUndefined)

def sign_url(base_url: str, job_id: str, tech_id: str, action: str, expiry: int = 600) -> str:
    """Generate a secure signed URL with JWT token."""
    payload = {
        "job_id": str(job_id),
        "tech_id": str(tech_id),
        "action": action,
        "exp": int(time.time()) + expiry
    }
    token = jwt.encode(payload, APP_SECRET, algorithm="HS256")
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}token={token}"

def get_action_urls(job_id: str, tech_id: str) -> dict:
    """Generate standard action URLs for a job."""
    return {
        "accept": sign_url(f"{BASE_API_URL}/jobs/{job_id}/accept", job_id, tech_id, "accept"),
        "reject": sign_url(f"{BASE_API_URL}/jobs/{job_id}/reject", job_id, tech_id, "reject"),
        "reassign": sign_url(f"{BASE_API_URL}/jobs/{job_id}/reassign", job_id, tech_id, "reassign")
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
    template = db.query(NotificationTemplate).filter(
        NotificationTemplate.type == template_type,
        NotificationTemplate.channel == channel,
        NotificationTemplate.locale == locale,
        NotificationTemplate.is_active == True,
        NotificationTemplate.tenant_id == "**platform**",
        NotificationTemplate.agent_type == "CommsAgent"
    ).first()
    
    # Fallback if no template exists for locale, try English
    if not template and locale != "en":
        template = db.query(NotificationTemplate).filter(
            NotificationTemplate.type == template_type,
            NotificationTemplate.channel == channel,
            NotificationTemplate.locale == "en",
            NotificationTemplate.is_active == True,
            NotificationTemplate.tenant_id == "**platform**",
            NotificationTemplate.agent_type == "CommsAgent"
        ).first()

    # Generic Fallback if still no template
    if not template:
        logger.warning(f"No active template found for {template_type}/{channel}/{locale}")
        return {
            "title": "New Notification",
            "body": "You have a new update. Please check the app."
        }

    # Inject standard action URLs if job and tech IDs exist in context
    if "job" in context and "tech" in context:
        try:
            job_id = context["job"].get("id", context["job"].get("job_id"))
            tech_id = context["tech"].get("id", context["tech"].get("tech_id"))
            if job_id and tech_id:
                context["action_urls"] = get_action_urls(job_id, tech_id)
        except AttributeError:
            pass # In case job/tech are not dicts

    try:
        title_text = None
        if template.title_template:
            t_title = jinja_env.from_string(template.title_template)
            title_text = t_title.render(**context)

        t_body = jinja_env.from_string(template.body_template)
        body_text = t_body.render(**context)

        return {
            "title": title_text,
            "body": body_text
        }
    except Exception as e:
        logger.error(f"Template rendering error for {template_type}/{channel}: {e}")
        return {
            "title": "System Alert",
            "body": "A new assignment is available. Please open the app."
        }

def render_preview(title_template: str, body_template: str, context: dict) -> dict:
    """Render a raw template string with mock context for the preview API."""
    title_text = None
    if title_template:
        t_title = jinja_env.from_string(title_template)
        title_text = t_title.render(**context)

    t_body = jinja_env.from_string(body_template)
    body_text = t_body.render(**context)

    return {
        "title": title_text,
        "body": body_text
    }
