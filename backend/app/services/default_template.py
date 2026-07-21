from sqlalchemy.orm import Session

from app.models import NotificationTemplate


# ==========================================================
# Supported Channels
# ==========================================================

SUPPORTED_CHANNELS = [
    "sms",
    "email",
    "push",
    "in_app",
]


# ==========================================================
# Supported Locales
# ==========================================================

SUPPORTED_LOCALES = {
    "en": "English",
}


# ==========================================================
# Notification Types
# ==========================================================

NOTIFICATION_TYPES = {
    "job_assigned": {
        "title": "Job Assigned",
        "sms": (
            "Hello {{customer_name}}, "
            "{{technician_name}} has been assigned to "
            "{{job_title}}. ETA: {{eta}}."
        ),
        "email": (
            """
            <h2>Job Assigned</h2>

            <p>Hello {{customer_name}},</p>

            <p>
                <strong>{{technician_name}}</strong> has been assigned
                to your service request.
            </p>

            <p>
                <strong>Job:</strong> {{job_title}}
            </p>

            <p>
                <strong>ETA:</strong> {{eta}}
            </p>

            <p>
                Thank you,<br>
                FieldOps Team
            </p>
            """
        ),
        "push": "{{technician_name}} assigned. ETA {{eta}}",
        "in_app": (
            "Your job '{{job_title}}' has been assigned to "
            "{{technician_name}}."
        ),

            # ======================================================
    # Technician Notifications
    # ======================================================

    "technician_job_assigned": {
        "title": "New Job Assignment",
        "sms": (
            "A new FieldOps job has been assigned. "
            "Open the app for details."
        ),
        "email": (
            """
            <h2>New Job Assignment</h2>
            <p>
                A new FieldOps job has been assigned to you.
                Open the technician app for details.
            </p>
            """
        ),
        "push": (
            "A new job has been assigned. "
            "Open FieldOps for details."
        ),
        "in_app": (
            "A new job has been assigned. "
            "Open FieldOps for details."
        ),
    },

    "technician_journey_started": {
        "title": "Journey Started",
        "sms": (
            "Your journey has started. "
            "Open FieldOps for job details."
        ),
        "email": (
            """
            <h2>Journey Started</h2>
            <p>
                Your journey has started.
                Open FieldOps for job details.
            </p>
            """
        ),
        "push": (
            "Journey started. "
            "Open FieldOps for job details."
        ),
        "in_app": (
            "Journey started. "
            "Open FieldOps for job details."
        ),
    },

    "technician_arrived_on_site": {
        "title": "Arrival Recorded",
        "sms": (
            "Your arrival has been recorded. "
            "Open FieldOps for job details."
        ),
        "email": (
            """
            <h2>Arrival Recorded</h2>
            <p>
                Your arrival at the job site has been recorded.
            </p>
            """
        ),
        "push": (
            "Your arrival at the job site was recorded."
        ),
        "in_app": (
            "Your arrival at the job site was recorded."
        ),
    },

    "technician_job_completed": {
        "title": "Job Completed",
        "sms": (
            "The job completion has been recorded in FieldOps."
        ),
        "email": (
            """
            <h2>Job Completed</h2>
            <p>
                The job completion has been recorded in FieldOps.
            </p>
            """
        ),
        "push": (
            "The job completion has been recorded."
        ),
        "in_app": (
            "The job completion has been recorded."
        ),
    },

    "technician_job_cancelled": {
        "title": "Job Cancelled",
        "sms": (
            "A FieldOps job was cancelled. "
            "Open the app for details."
        ),
        "email": (
            """
            <h2>Job Cancelled</h2>
            <p>
                A FieldOps job assigned to you was cancelled.
                Open the app for details.
            </p>
            """
        ),
        "push": (
            "A FieldOps job was cancelled. "
            "Open the app for details."
        ),
        "in_app": (
            "A FieldOps job was cancelled. "
            "Open the app for details."
        ),
    },

    # ======================================================
    # Dispatcher Notifications
    # ======================================================

    "dispatcher_job_assigned": {
        "title": "Job Assigned",
        "sms": (
            "Assignment confirmed for {{job_title}}."
        ),
        "email": (
            """
            <h2>Job Assigned</h2>
            <p>
                Assignment confirmed for {{job_title}}.
            </p>
            """
        ),
        "push": (
            "Assignment confirmed for {{job_title}}."
        ),
        "in_app": (
            "Assignment confirmed for {{job_title}}."
        ),
    },

    "dispatcher_en_route": {
        "title": "Technician En Route",
        "sms": (
            "{{technician_name}} is en route. "
            "ETA: {{eta}}."
        ),
        "email": (
            """
            <h2>Technician En Route</h2>
            <p>
                {{technician_name}} is en route.
                ETA: {{eta}}.
            </p>
            """
        ),
        "push": (
            "{{technician_name}} is en route."
        ),
        "in_app": (
            "{{technician_name}} is en route. "
            "ETA: {{eta}}."
        ),
    },

    "dispatcher_on_site": {
        "title": "Technician On Site",
        "sms": (
            "{{technician_name}} is now on site."
        ),
        "email": (
            """
            <h2>Technician On Site</h2>
            <p>
                {{technician_name}} is now on site.
            </p>
            """
        ),
        "push": (
            "{{technician_name}} is now on site."
        ),
        "in_app": (
            "{{technician_name}} is now on site."
        ),
    },

    "dispatcher_completed": {
        "title": "Job Completed",
        "sms": (
            "{{job_title}} has been completed."
        ),
        "email": (
            """
            <h2>Job Completed</h2>
            <p>
                {{job_title}} has been completed.
            </p>
            """
        ),
        "push": (
            "{{job_title}} has been completed."
        ),
        "in_app": (
            "{{job_title}} has been completed."
        ),
    },

    "dispatcher_cancelled": {
        "title": "Job Cancelled",
        "sms": (
            "{{job_title}} has been cancelled."
        ),
        "email": (
            """
            <h2>Job Cancelled</h2>
            <p>
                {{job_title}} has been cancelled.
            </p>
            """
        ),
        "push": (
            "{{job_title}} has been cancelled."
        ),
        "in_app": (
            "{{job_title}} has been cancelled."
        ),
    },
    },

    "technician_en_route": {
        "title": "Technician En Route",
        "sms": (
            "Hello {{customer_name}}, "
            "{{technician_name}} is on the way. "
            "Expected arrival: {{eta}}."
        ),
        "email": (
            """
            <h2>Technician En Route</h2>

            <p>Hello {{customer_name}},</p>

            <p>
                {{technician_name}} is currently travelling to your location.
            </p>

            <p>
                ETA : <strong>{{eta}}</strong>
            </p>

            <p>
                Thank you,<br>
                FieldOps Team
            </p>
            """
        ),
        "push": "{{technician_name}} is on the way.",
        "in_app": "{{technician_name}} is en route to your location."
    },

    "technician_arrived": {
        "title": "Technician Arrived",
        "sms": (
            "Hello {{customer_name}}, "
            "{{technician_name}} has arrived "
            "for {{job_title}}."
        ),
        "email": (
            """
            <h2>Technician Arrived</h2>

            <p>Hello {{customer_name}},</p>

            <p>
                {{technician_name}} has arrived at your location
                and will begin work shortly.
            </p>

            <p>
                Job : {{job_title}}
            </p>

            <p>
                Thank you,<br>
                FieldOps Team
            </p>
            """
        ),
        "push": "{{technician_name}} has arrived.",
        "in_app": "{{technician_name}} has arrived."
    },

    "job_completed": {
        "title": "Job Completed",
        "sms": (
            "Hello {{customer_name}}, "
            "{{job_title}} has been completed successfully. "
            "Thank you for choosing us."
        ),
        "email": (
            """
            <h2>Job Completed</h2>

            <p>Hello {{customer_name}},</p>

            <p>
                Your service request has been completed successfully.
            </p>

            <p>
                Job : {{job_title}}
            </p>

            <p>
                Thank you for choosing FieldOps.
            </p>
            """
        ),
        "push": "{{job_title}} completed successfully.",
        "in_app": "{{job_title}} has been completed."
    },

    "job_cancelled": {
        "title": "Job Cancelled",
        "sms": (
            "Hello {{customer_name}}, "
            "your {{job_title}} has been cancelled."
        ),
        "email": (
            """
            <h2>Job Cancelled</h2>

            <p>Hello {{customer_name}},</p>

            <p>
                Unfortunately your service request
                has been cancelled.
            </p>

            <p>
                Job : {{job_title}}
            </p>

            <p>
                Please contact support for assistance.
            </p>
            """
        ),
        "push": "{{job_title}} cancelled.",
        "in_app": "Your job '{{job_title}}' has been cancelled."
    },

    "eta_updated": {
        "title": "ETA Updated",
        "sms": (
            "Hello {{customer_name}}, "
            "updated ETA for {{technician_name}} "
            "is {{eta}}."
        ),
        "email": (
            """
            <h2>ETA Updated</h2>

            <p>Hello {{customer_name}},</p>

            <p>
                Your technician's estimated arrival
                time has changed.
            </p>

            <p>
                New ETA :
                <strong>{{eta}}</strong>
            </p>

            <p>
                Thank you,<br>
                FieldOps Team
            </p>
            """
        ),
        "push": "Updated ETA: {{eta}}",
        "in_app": "Your ETA has been updated to {{eta}}."
    },
}


# ==========================================================
# Helper Functions
# ==========================================================

def get_format(channel: str) -> str:
    if channel == "email":
        return "html"

    return "text"


def build_template_name(title: str, channel: str, locale: str) -> str:
    language = SUPPORTED_LOCALES[locale]
    return f"{title} ({channel.upper()} - {language})"


def generate_default_templates():

    templates = []

    for locale in SUPPORTED_LOCALES:

        for channel in SUPPORTED_CHANNELS:

            for template_type, template in NOTIFICATION_TYPES.items():

                body = template[channel]

                # Derive variables automatically
                from jinja2 import Environment, meta
                env = Environment()
                ast = env.parse(body)
                vars_set = meta.find_undeclared_variables(ast)
                if template["title"]:
                    ast_title = env.parse(template["title"])
                    vars_set.update(meta.find_undeclared_variables(ast_title))
                variables = list(vars_set)

                templates.append(
                    {
                        "name": build_template_name(
                            template["title"],
                            channel,
                            locale,
                        ),
                        "type": template_type,
                        "channel": channel,
                        "locale": locale,
                        "format": get_format(channel),
                        "title_template": template["title"],
                        "body_template": body,
                        "variables": variables,
                        "tenant_id": "**platform**",
                        "agent_type": "CommsAgent"
                    }
                )

    return templates
def seed_default_templates(db: Session):
    """
    Seed the database with default notification templates.
    """

    templates = generate_default_templates()

    for template in templates:

        existing_template = (
            db.query(NotificationTemplate)
            .filter_by(
                type=template["type"],
                channel=template["channel"],
                locale=template["locale"],
                tenant_id="**platform**",
                agent_type="CommsAgent"
            )
            .first()
        )

        if not existing_template:
            new_template = NotificationTemplate(**template)
            db.add(new_template)

    db.commit()