from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import EnterpriseAuditLog
from app.services.ai.FieldOpsAI.schemas.intent import (
    IntentContext,
    IntentResult,
)
from app.services.ai.FieldOpsAI.services.intent_service import IntentService


# ==========================================================
# Test database
# ==========================================================

TestingEngine = create_engine(
    "sqlite://",
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

EnterpriseAuditLog.__table__.create(
    bind=TestingEngine,
)

TestingSessionLocal = sessionmaker(
    bind=TestingEngine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Provide the real test database session."""
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ==========================================================
# Fake Intent Engine
# ==========================================================

class FakeIntentEngine:
    def recognize(self, context: IntentContext) -> IntentResult:
        return IntentResult(
            intent="CANCELLATION",
            confidence=0.90,
            requires_human=False,
        )


# ==========================================================
# Test
# ==========================================================

def test_intent_service_creates_audit_log(
    db_session: Session,
) -> None:
    service = IntentService(
        db=db_session,
        engine=FakeIntentEngine(),
    )

    result = service.recognize(
        IntentContext(
            message="Please cancel my appointment.",
            language="en",
        ),
        tenant_id="tenant-1",
        user_id="user-1",
        user_email="customer@example.com",
        role="CUSTOMER",
    )

    db_session.commit()

    assert result.intent == "CANCELLATION"

    audit = (
        db_session.query(EnterpriseAuditLog)
        .filter(
            EnterpriseAuditLog.action == "INTENT_CLASSIFIED"
        )
        .first()
    )

    assert audit is not None
    assert audit.tenant_id == "tenant-1"
    assert audit.user_id == "user-1"
    assert audit.entity_type == "customer_message"

    assert audit.details["intent"] == "CANCELLATION"
    assert audit.details["confidence"] == 0.90
    assert audit.details["requires_human"] is False
    assert audit.details["language"] == "en"