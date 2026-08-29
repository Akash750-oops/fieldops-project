from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.jwt_handler import create_access_token
from app.auth.rbac import UserRole
from app.database import get_db
from app.main import app
from app.models import User, Organization


TEST_TENANT_ID = "test-tenant-admin-queue"


@pytest.fixture
def db():
    from app.database import SessionLocal

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.pop(get_db, None)


def create_test_user(
    db,
    role: UserRole,
    tenant_id: str = TEST_TENANT_ID,
) -> User:
    organization = db.query(Organization).filter(
        Organization.id == tenant_id
    ).first()

    if organization is None:
        organization = Organization(
            id=tenant_id,
            name=f"Test Organization {tenant_id}",
            slug=f"test-org-{uuid.uuid4().hex[:12]}",
        )

        db.add(organization)
        db.flush()

    user = User(
        id=str(uuid.uuid4()),
        email=f"{uuid.uuid4()}@example.com",
        password_hash="test-password-hash",
        first_name="Queue",
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


def test_queue_stats_requires_authentication(client):
    response = client.get("/admin/queue/stats")

    assert response.status_code == 401


@pytest.mark.parametrize(
    "role",
    [
        UserRole.HEAD,
        UserRole.TECHNICIAN,
        UserRole.CUSTOMER,
    ],
)
def test_queue_stats_rejects_users_without_queue_permission(
    client,
    db,
    role,
):
    user = create_test_user(db, role)
    token = create_token(user)

    response = client.get(
        "/admin/queue/stats",
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
def test_queue_stats_allows_users_with_queue_permission(
    client,
    db,
    role,
):
    user = create_test_user(db, role)
    token = create_token(user)

    response = client.get(
        "/admin/queue/stats",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200


def test_queue_stats_uses_authenticated_tenant(
    client,
    db,
):
    user = create_test_user(
        db,
        UserRole.DISPATCHER,
        tenant_id="tenant-authenticated",
    )

    token = create_token(user)

    response = client.get(
        "/admin/queue/stats",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tenant-other",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "depth" in data
    assert "oldest_task_age" in data
    assert "throughput" in data