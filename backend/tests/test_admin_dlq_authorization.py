from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.jwt_handler import create_access_token
from app.auth.rbac import UserRole
from app.database import get_db, SessionLocal
from app.main import app
from app.models import User, DeadLetterTask, Organization


TEST_TENANT_ID = "test-tenant-dlq"


@pytest.fixture
def db():
    session = SessionLocal()

    try:
        # Clean DLQ records before each test so tests are isolated.
        session.query(DeadLetterTask).delete()
        session.commit()

        yield session

    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.pop(get_db, None)


def create_test_organization(
    db,
    tenant_id: str,
) -> Organization:
    """
    Create the organization required by the User.tenant_id
    foreign-key constraint.
    """

    organization = (
        db.query(Organization)
        .filter(Organization.id == tenant_id)
        .first()
    )

    if organization is None:
        organization = Organization(
            id=tenant_id,
            name=f"DLQ Test Organization {tenant_id}",
            slug=f"dlq-test-{uuid.uuid4().hex[:8]}",
        )

        db.add(organization)
        db.commit()
        db.refresh(organization)

    return organization


def create_test_user(
    db,
    role: UserRole,
    tenant_id: str = TEST_TENANT_ID,
) -> User:
    """
    Create a test user together with its organization.
    """

    # User.tenant_id references organizations.id,
    # so the organization must exist first.
    create_test_organization(
        db,
        tenant_id,
    )

    user = User(
        id=str(uuid.uuid4()),
        email=f"{uuid.uuid4()}@example.com",
        password_hash="test-password-hash",
        first_name="DLQ",
        last_name="Tester",
        role=role.value,
        tenant_id=tenant_id,
        is_active=True,
        deleted_at=None,
        locked_until=None,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_token(user: User) -> str:
    return create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )


def create_dlq_item(
    db,
    tenant_id: str = TEST_TENANT_ID,
) -> DeadLetterTask:
    """
    Create a test DLQ item.

    Ensure the tenant organization exists because this test
    represents a real tenant in the system.
    """

    create_test_organization(
        db,
        tenant_id,
    )

    item = DeadLetterTask(
        id=str(uuid.uuid4()),
        task_id=str(uuid.uuid4()),
        celery_task_id=str(uuid.uuid4()),
        task_type="TEST_TASK",
        tenant_id=tenant_id,
        payload={
            "task_type": "TEST_TASK",
            "data": {
                "test": True,
            },
        },
        context={
            "source": "test",
        },
        reason="test_failure",
        error_type="RuntimeError",
        error_message="Test failure",
        retry_count=3,
        status="FAILED",
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


# ==========================================================
# Authentication
# ==========================================================


def test_list_dlq_requires_authentication(client):
    response = client.get("/admin/dlq")

    assert response.status_code == 401


# ==========================================================
# Permission checks
# ==========================================================


@pytest.mark.parametrize(
    "role",
    [
        UserRole.HEAD,
        UserRole.TECHNICIAN,
        UserRole.CUSTOMER,
    ],
)
def test_list_dlq_rejects_users_without_permission(
    client,
    db,
    role,
):
    user = create_test_user(
        db,
        role,
    )

    token = create_token(user)

    response = client.get(
        "/admin/dlq",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "role",
    [
        UserRole.DISPATCHER,
        UserRole.SUPER_ADMIN,
    ],
)
def test_list_dlq_allows_authorized_users(
    client,
    db,
    role,
):
    user = create_test_user(
        db,
        role,
    )

    token = create_token(user)

    response = client.get(
        "/admin/dlq",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200


# ==========================================================
# Tenant isolation
# ==========================================================


def test_list_dlq_uses_authenticated_tenant(
    client,
    db,
):
    authenticated_tenant = "tenant-authenticated"
    other_tenant = "tenant-other"

    user = create_test_user(
        db,
        UserRole.DISPATCHER,
        tenant_id=authenticated_tenant,
    )

    create_dlq_item(
        db,
        tenant_id=authenticated_tenant,
    )

    create_dlq_item(
        db,
        tenant_id=other_tenant,
    )

    token = create_token(user)

    response = client.get(
        "/admin/dlq",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": other_tenant,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert data["items"][0]["tenant_id"] == authenticated_tenant


# ==========================================================
# Missing DLQ item
# ==========================================================


def test_requeue_missing_dlq_item_returns_404(
    client,
    db,
):
    user = create_test_user(
        db,
        UserRole.DISPATCHER,
    )

    token = create_token(user)

    response = client.post(
        f"/admin/dlq/{uuid.uuid4()}/requeue",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404


def test_delete_missing_dlq_item_returns_404(
    client,
    db,
):
    user = create_test_user(
        db,
        UserRole.DISPATCHER,
    )

    token = create_token(user)

    response = client.delete(
        f"/admin/dlq/{uuid.uuid4()}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404


# ==========================================================
# Cross-tenant protection
# ==========================================================


def test_requeue_rejects_wrong_tenant(
    client,
    db,
):
    user_tenant = "tenant-a"
    dlq_tenant = "tenant-b"

    user = create_test_user(
        db,
        UserRole.DISPATCHER,
        tenant_id=user_tenant,
    )

    item = create_dlq_item(
        db,
        tenant_id=dlq_tenant,
    )

    token = create_token(user)

    response = client.post(
        f"/admin/dlq/{item.id}/requeue",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404


def test_delete_rejects_wrong_tenant(
    client,
    db,
):
    user_tenant = "tenant-a"
    dlq_tenant = "tenant-b"

    user = create_test_user(
        db,
        UserRole.DISPATCHER,
        tenant_id=user_tenant,
    )

    item = create_dlq_item(
        db,
        tenant_id=dlq_tenant,
    )

    token = create_token(user)

    response = client.delete(
        f"/admin/dlq/{item.id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404