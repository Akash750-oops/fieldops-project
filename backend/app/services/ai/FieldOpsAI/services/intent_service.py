"""
intent_service.py

Service layer for customer intent recognition.

Responsibilities:
- Run IntentEngine.
- Persist INTENT_CLASSIFIED audit events.
- Keep database operations outside IntentEngine.
"""

from sqlalchemy.orm import Session

from app.services.ai.FieldOpsAI.agents.intent_engine import IntentEngine
from app.services.ai.FieldOpsAI.schemas.intent import (
    IntentContext,
    IntentResult,
)
from app.services.enterprise_audit import audit_log, AuditAction


class IntentService:
    """
    DB-aware service for intent recognition and auditing.
    """

    def __init__(
        self,
        db: Session,
        engine: IntentEngine | None = None,
    ) -> None:
        self.db = db
        self.engine = engine or IntentEngine()

    def recognize(
        self,
        context: IntentContext,
        *,
        tenant_id: str,
        user_id: str | None = None,
        user_email: str | None = None,
        role: str | None = None,
        entity_type: str = "customer_message",
        entity_id: str | None = None,
    ) -> IntentResult:
        """
        Recognize customer intent and create an audit record.
        """

        result = self.engine.recognize(context)

        audit_log(
            self.db,
            action=AuditAction.INTENT_CLASSIFIED,
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            role=role,
            entity_type=entity_type,
            entity_id=entity_id,
            details={
                "intent": result.intent.value
                if hasattr(result.intent, "value")
                else result.intent,
                "confidence": result.confidence,
                "requires_human": result.requires_human,
                "language": context.language,
            },
        )

        self.db.commit()

        return result