"""
Integration tests for the message preview and approval API routes.

These tests exercise the real FastAPI endpoints in
app/routes/message_preview.py via TestClient, following the same
pattern as tests/test_brand_safety_admin_routes.py:

- real in-memory SQLite database
- get_db overridden with the test session
- get_current_user overridden with a fake authenticated user
  (no real JWT needed)
- CommunicationService replaced, inside the routes module
  namespace, with a factory that builds the real
  CommunicationService using the existing deterministic
  PreviewAgent / build_service test helpers, so no external AI
  provider or HMAC secret is required.

No SMS/email is actually sent by any of these tests.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models import (
    AIBrandSafetyRule,
    AIGuardrailViolation,
    NotificationTemplate,
    EnterpriseAuditLog,
)
from app.routes import message_preview as message_preview_routes
from app.routes.message_preview import router

from tests.test_communication_service import build_service
from tests.test_message_preview import PreviewAgent


# ==========================================================
# Test database
# ==========================================================


@pytest.fixture
def db_session() -> Iterator[Session]:
    """
    Create an isolated in-memory database containing only the
    tables the preview + communication workflow requires.
    """

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    NotificationTemplate.__table__.create(bind=engine)
    AIBrandSafetyRule.__table__.create(bind=engine)
    AIGuardrailViolation.__table__.create(bind=engine)
    EnterpriseAuditLog.__table__.create(bind=engine)

    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    session = testing_session()

    try:
        yield session
    finally:
        session.close()
        EnterpriseAuditLog.__table__.drop(bind=engine)
        AIGuardrailViolation.__table__.drop(bind=engine)
        AIBrandSafetyRule.__table__.drop(bind=engine)
        NotificationTemplate.__table__.drop(bind=engine)
        engine.dispose()


# ==========================================================
# Fake authenticated user
# ==========================================================


class FakeUser:
    """
    Minimal stand-in for AuthenticatedUser. get_current_user is
    fully overridden in these tests, so no real JWT is decoded.
    """

    def __init__(
        self,
        *,
        user_id: str = "operator-1",
        tenant_id: str = "tenant-1",
        role: str = "DISPATCHER",
        email: str = "operator@example.com",
    ) -> None:
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.email = email


# ==========================================================
# Route client fixture
# ==========================================================


@pytest.fixture
def route_client(
    db_session: Session,
) -> Iterator[TestClient]:
    """
    Build a small FastAPI app using the real message_preview
    router, with get_db / get_current_user overridden and
    CommunicationService replaced by a deterministic test double
    inside the routes module namespace.

    The in-memory preview registry (_preview_services /
    MessagePreview._previews) is module-level state, so it is
    reset before each test to keep tests isolated from each
    other.
    """

    message_preview_routes._preview_services.clear()

    def fake_communication_service(*, db, tenant_id):
        return build_service(
            db,
            agent=PreviewAgent(),
            tenant_id=tenant_id,
        )

    original_communication_service = (
        message_preview_routes.CommunicationService
    )
    message_preview_routes.CommunicationService = (
        fake_communication_service
    )

    test_app = FastAPI()
    test_app.include_router(router)

    def override_get_db() -> Iterator[Session]:
        yield db_session

    def override_get_current_user() -> FakeUser:
        return FakeUser()

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    try:
        with TestClient(test_app) as client:
            yield client
    finally:
        message_preview_routes.CommunicationService = (
            original_communication_service
        )
        message_preview_routes._preview_services.clear()


# ==========================================================
# Helpers
# ==========================================================


def build_context_payload(
    *,
    channel: str = "SMS",
) -> dict:
    """Build a valid CommunicationContext JSON payload."""

    return {
        "job_id": "JOB-1001",
        "correlation_id": "correlation-1001",
        "notification_type": "job_assigned",
        "recipient_type": "CUSTOMER",
        "channel": channel,
        "locale": "en",
        "customer_name": "Ruby Devi",
        "technician_name": "Arun Kumar",
        "job_status": "ASSIGNED",
        "job_title": "Air conditioner repair",
        "eta": "30 minutes",
        "sentiment": "NEUTRAL",
    }


def build_preview_payload(
    *,
    priority: str | None = None,
    first_time_template: bool = False,
) -> dict:
    return {
        "context": build_context_payload(),
        "template_key": "job_assigned",
        "priority": priority,
        "first_time_template": first_time_template,
    }


def create_preview(
    client: TestClient,
    *,
    priority: str | None = None,
    first_time_template: bool = False,
) -> dict:
    response = client.post(
        "/messages/preview",
        json=build_preview_payload(
            priority=priority,
            first_time_template=first_time_template,
        ),
    )

    assert response.status_code == 200

    return response.json()


# ==========================================================
# Preview endpoint
# ==========================================================


def test_create_preview_returns_sms_and_email(
    route_client: TestClient,
) -> None:
    """POST /messages/preview generates both channel previews."""

    body = create_preview(route_client)

    assert body["preview_id"]
    assert body["template_key"] == "job_assigned"

    assert body["sms"] is not None
    assert body["sms"]["channel"] == "sms"
    assert body["sms"]["body"]
    assert body["sms"]["character_limit"] == 160

    assert body["email"] is not None
    assert body["email"]["channel"] == "email"
    assert body["email"]["body"]


def test_create_preview_high_priority_requires_approval(
    route_client: TestClient,
) -> None:
    """HIGH priority previews are flagged as requiring approval."""

    body = create_preview(route_client, priority="HIGH")

    assert body["requires_approval"] is True
    assert "HIGH" in body["approval_reason"].upper()


def test_create_preview_normal_does_not_require_approval(
    route_client: TestClient,
) -> None:
    """Normal previews do not require approval."""

    body = create_preview(route_client, priority="NORMAL")

    assert body["requires_approval"] is False
    assert body["approval_reason"] is None


def test_create_preview_rejects_empty_template_key(
    route_client: TestClient,
) -> None:
    """An empty template_key is rejected with 422."""

    payload = build_preview_payload()
    payload["template_key"] = "   "

    response = route_client.post(
        "/messages/preview",
        json=payload,
    )

    assert response.status_code == 422


# ==========================================================
# Edit endpoint
# ==========================================================


def test_edit_preview_saves_operator_changes(
    route_client: TestClient,
) -> None:
    """PATCH /messages/{id} saves an operator edit and returns it."""

    preview = create_preview(route_client)

    edited_sms = "Hello Ruby, your technician is on the way."

    response = route_client.patch(
        f"/messages/{preview['preview_id']}",
        json={"edited_messages": {"sms": edited_sms}},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["sms"]["body"] == edited_sms
    assert body["sms"]["character_count"] == len(edited_sms)


def test_edit_preview_rejects_oversized_sms(
    route_client: TestClient,
) -> None:
    """An SMS edit over 160 characters is rejected with 422."""

    preview = create_preview(route_client)

    response = route_client.patch(
        f"/messages/{preview['preview_id']}",
        json={"edited_messages": {"sms": "x" * 161}},
    )

    assert response.status_code == 422


def test_edit_unknown_preview_returns_404(
    route_client: TestClient,
) -> None:
    """Editing a preview ID that was never created returns 404."""

    response = route_client.patch(
        "/messages/does-not-exist",
        json={"edited_messages": {"sms": "Hello"}},
    )

    assert response.status_code == 404


# ==========================================================
# Approval endpoint
# ==========================================================


def test_approve_high_priority_preview_succeeds(
    route_client: TestClient,
) -> None:
    """A HIGH priority preview can be approved by the operator."""

    preview = create_preview(route_client, priority="HIGH")

    response = route_client.post(
        f"/messages/{preview['preview_id']}/approve"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["approved"] is True
    assert body["approved_by"] == "operator-1"
    assert body["preview_id"] == preview["preview_id"]
    assert (
        body["original_messages"]["sms"]
        == preview["sms"]["body"]
    )


def test_approve_normal_preview_is_rejected(
    route_client: TestClient,
) -> None:
    """A preview that does not require approval cannot be approved."""

    preview = create_preview(route_client, priority="NORMAL")

    response = route_client.post(
        f"/messages/{preview['preview_id']}/approve"
    )

    assert response.status_code == 422


def test_approve_unknown_preview_returns_404(
    route_client: TestClient,
) -> None:
    """Approving an unknown preview ID returns 404."""

    response = route_client.post(
        "/messages/does-not-exist/approve"
    )

    assert response.status_code == 404


def test_approve_persists_audit_record(
    route_client: TestClient,
    db_session: Session,
) -> None:
    """Approval via the API persists a real EnterpriseAuditLog row."""

    preview = create_preview(route_client, priority="URGENT")

    response = route_client.post(
        f"/messages/{preview['preview_id']}/approve"
    )

    assert response.status_code == 200

    record = (
        db_session.query(EnterpriseAuditLog)
        .filter(
            EnterpriseAuditLog.entity_id
            == preview["preview_id"]
        )
        .one()
    )

    assert record.user_id == "operator-1"
    assert record.tenant_id == "tenant-1"


# ==========================================================
# Tenant isolation
# ==========================================================


def test_edit_across_tenants_returns_404(
    route_client: TestClient,
) -> None:
    """
    A preview created under one tenant cannot be edited by a
    request authenticated as a different tenant.
    """

    preview = create_preview(route_client)

    def override_other_tenant_user() -> FakeUser:
        return FakeUser(tenant_id="tenant-2")

    route_client.app.dependency_overrides[
        get_current_user
    ] = override_other_tenant_user

    response = route_client.patch(
        f"/messages/{preview['preview_id']}",
        json={"edited_messages": {"sms": "Hello"}},
    )

    assert response.status_code == 404


def test_approve_across_tenants_returns_404(
    route_client: TestClient,
) -> None:
    """
    A preview created under one tenant cannot be approved by a
    request authenticated as a different tenant.
    """

    preview = create_preview(route_client, priority="HIGH")

    def override_other_tenant_user() -> FakeUser:
        return FakeUser(tenant_id="tenant-2")

    route_client.app.dependency_overrides[
        get_current_user
    ] = override_other_tenant_user

    response = route_client.post(
        f"/messages/{preview['preview_id']}/approve"
    )

    assert response.status_code == 404