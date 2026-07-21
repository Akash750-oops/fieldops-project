from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base
from app.redis_client import get_redis_client
from app.services.ai.FieldOpsAI.repositories.prompt_template_repository import (
    PromptTemplateRepository,
    RepositoryError,
)


# ==========================================================
# Test configuration
# ==========================================================


TEST_JWT_SECRET = "test-jwt-secret"
TEST_JWT_ALGORITHM = "HS256"


# ==========================================================
# Test database
# ==========================================================


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ==========================================================
# Fake Redis
# ==========================================================


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self.expires: dict[str, int] = {}
        self.deleted_keys: list[str] = []

    def get(
        self,
        key: str,
    ) -> Any:
        return self.data.get(key)

    def setex(
        self,
        key: str,
        ttl: int,
        value: Any,
    ) -> bool:
        self.data[key] = value
        self.expires[key] = ttl
        return True

    def incr(
        self,
        key: str,
        amount: int = 1,
    ) -> int:
        current = int(
            self.data.get(
                key,
                0,
            )
        )

        updated = current + amount
        self.data[key] = updated

        return updated

    def delete(
        self,
        key: str,
    ) -> int:
        self.deleted_keys.append(key)
        self.data.pop(key, None)
        self.expires.pop(key, None)
        return 1

    def reset(self) -> None:
        self.data.clear()
        self.expires.clear()
        self.deleted_keys.clear()


fake_redis = FakeRedis()


# ==========================================================
# Fixtures
# ==========================================================


@pytest.fixture
def api_client(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Create one isolated API client per test.

    Each test receives:

    - A fresh SQLite schema
    - A clean Redis fake
    - A configured JWT secret
    - Fresh FastAPI dependency overrides
    """

    monkeypatch.setenv(
        "JWT_SECRET",
        TEST_JWT_SECRET,
    )

    monkeypatch.setenv(
        "JWT_ALGORITHM",
        TEST_JWT_ALGORITHM,
    )

    app.dependency_overrides.clear()

    Base.metadata.drop_all(
        bind=engine
    )

    Base.metadata.create_all(
        bind=engine
    )

    fake_redis.reset()

    def override_get_db():
        db: Session = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    def override_get_redis_client():
        return fake_redis

    app.dependency_overrides[
        get_db
    ] = override_get_db

    app.dependency_overrides[
        get_redis_client
    ] = override_get_redis_client

    client = TestClient(app)

    try:
        yield client
    finally:
        client.close()

        app.dependency_overrides.clear()

        Base.metadata.drop_all(
            bind=engine
        )

        fake_redis.reset()


# ==========================================================
# JWT helpers
# ==========================================================


def create_test_jwt(
    *,
    tenant_id: str = "tenant_1",
    user_id: str = "user_1",
    roles: Any = None,
    expires_in_minutes: int = 15,
    secret: str = TEST_JWT_SECRET,
    include_tenant: bool = True,
    include_user: bool = True,
    include_roles: bool = True,
) -> str:
    """
    Create a real signed JWT accepted by the production
    prompt-admin dependency.
    """

    if roles is None:
        roles = ["admin"]

    payload: dict[str, Any] = {
        "exp": (
            datetime.now(timezone.utc)
            + timedelta(
                minutes=expires_in_minutes
            )
        ),
    }

    if include_tenant:
        payload["tenant_id"] = tenant_id

    if include_user:
        payload["sub"] = user_id

    if include_roles:
        payload["roles"] = roles

    return jwt.encode(
        payload,
        secret,
        algorithm=TEST_JWT_ALGORITHM,
    )


def get_headers(
    *,
    role: str = "admin",
    roles: Any = None,
    tenant: str = "tenant_1",
    user_id: str = "user_1",
    include_consistency_headers: bool = True,
) -> dict[str, str]:
    if roles is None:
        roles = [role]

    token = create_test_jwt(
        tenant_id=tenant,
        user_id=user_id,
        roles=roles,
    )

    headers = {
        "Authorization": (
            f"Bearer {token}"
        ),
    }

    if include_consistency_headers:
        headers["X-Tenant-ID"] = tenant
        headers["X-User-ID"] = user_id

    return headers


def prompt_payload(
    *,
    name: str = "Test Prompt",
    prompt_status: str = "default",
    body: str = "Hello {{ name }}",
    variables: list[str] | None = None,
    agent_type: str = "CommsAgent",
    channel: str = "sms",
    language: str = "en",
    version: int = 1,
) -> dict[str, Any]:
    if variables is None:
        variables = ["name"]

    return {
        "name": name,
        "agent_type": agent_type,
        "channel": channel,
        "language": language,
        "status": prompt_status,
        "body": body,
        "variables": variables,
        "version": version,
    }


# ==========================================================
# Authentication tests
# ==========================================================


def test_authentication_is_required(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/admin/prompts"
    )

    # HTTPBearer may use either 401 or 403 depending on
    # the installed FastAPI/Starlette version.
    assert response.status_code in {
        401,
        403,
    }


def test_invalid_signature_returns_401(
    api_client: TestClient,
) -> None:
    token = create_test_jwt(
        secret="wrong-secret",
    )

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid token."
    )


def test_expired_token_returns_401(
    api_client: TestClient,
) -> None:
    token = create_test_jwt(
        expires_in_minutes=-1,
    )

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Token has expired."
    )


def test_missing_jwt_secret_fails_closed(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "JWT_SECRET",
        raising=False,
    )

    token = create_test_jwt()

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Authentication service unavailable."
    )


def test_forbidden_role_returns_403(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/admin/prompts",
        headers=get_headers(
            role="technician"
        ),
    )

    assert response.status_code == 403


def test_roles_string_is_supported(
    api_client: TestClient,
) -> None:
    token = create_test_jwt(
        roles="admin",
    )

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
        },
    )

    assert response.status_code == 200


def test_comma_separated_roles_string_is_supported(
    api_client: TestClient,
) -> None:
    token = create_test_jwt(
        roles="manager,admin",
    )

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
        },
    )

    assert response.status_code == 200


def test_roles_list_is_supported(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/admin/prompts",
        headers=get_headers(
            roles=[
                "manager",
                "admin",
            ]
        ),
    )

    assert response.status_code == 200


def test_missing_tenant_claim_returns_403(
    api_client: TestClient,
) -> None:
    token = create_test_jwt(
        include_tenant=False,
    )

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
        },
    )

    assert response.status_code == 403


def test_missing_user_claim_returns_403(
    api_client: TestClient,
) -> None:
    token = create_test_jwt(
        include_user=False,
    )

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
        },
    )

    assert response.status_code == 403


def test_missing_roles_claim_returns_403(
    api_client: TestClient,
) -> None:
    token = create_test_jwt(
        include_roles=False,
    )

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
        },
    )

    assert response.status_code == 403


def test_tenant_header_mismatch_returns_403(
    api_client: TestClient,
) -> None:
    token = create_test_jwt(
        tenant_id="tenant_1",
    )

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
            "X-Tenant-ID": "tenant_2",
        },
    )

    assert response.status_code == 403


def test_user_header_mismatch_returns_403(
    api_client: TestClient,
) -> None:
    token = create_test_jwt(
        user_id="user_1",
    )

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
            "X-User-ID": "user_2",
        },
    )

    assert response.status_code == 403


def test_permission_header_cannot_add_role(
    api_client: TestClient,
) -> None:
    token = create_test_jwt(
        roles=["admin"],
    )

    response = api_client.get(
        "/admin/prompts",
        headers={
            "Authorization": (
                f"Bearer {token}"
            ),
            "X-Permissions": (
                "admin,super_admin"
            ),
        },
    )

    assert response.status_code == 403


def test_platform_requires_super_admin(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/admin/prompts",
        headers=get_headers(
            tenant="**platform**",
            roles=["admin"],
        ),
    )

    assert response.status_code == 403


def test_platform_accepts_multiple_roles_with_super_admin(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/admin/prompts",
        headers=get_headers(
            tenant="**platform**",
            roles=[
                "admin",
                "super_admin",
            ],
        ),
    )

    assert response.status_code == 200


# ==========================================================
# CRUD API tests
# ==========================================================


def test_post_works(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/admin/prompts",
        json=prompt_payload(),
        headers=get_headers(),
    )

    assert response.status_code == 201

    result = response.json()

    assert result["name"] == "Test Prompt"
    assert result["agent_type"] == "CommsAgent"
    assert result["channel"] == "sms"
    assert result["language"] == "en"
    assert result["status"] == "default"


def test_get_collection(
    api_client: TestClient,
) -> None:
    create_response = api_client.post(
        "/admin/prompts",
        json=prompt_payload(
            prompt_status="collection",
            body="Collection prompt",
            variables=[],
        ),
        headers=get_headers(),
    )

    assert create_response.status_code == 201

    response = api_client.get(
        "/admin/prompts",
        params={
            "channel": "sms",
        },
        headers=get_headers(),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_lookup(
    api_client: TestClient,
) -> None:
    create_response = api_client.post(
        "/admin/prompts",
        json=prompt_payload(
            prompt_status="lookup",
            body="Lookup prompt",
            variables=[],
        ),
        headers=get_headers(),
    )

    assert create_response.status_code == 201

    response = api_client.get(
        "/admin/prompts/lookup",
        params={
            "agent_type": "CommsAgent",
            "channel": "sms",
            "language": "en",
            "status": "lookup",
        },
        headers=get_headers(),
    )

    assert response.status_code == 200
    assert response.json()["source"] == "tenant"
    assert response.json()["body"] == "Lookup prompt"


def test_get_by_id(
    api_client: TestClient,
) -> None:
    create_response = api_client.post(
        "/admin/prompts",
        json=prompt_payload(
            prompt_status="get_by_id",
            body="Get by ID",
            variables=[],
        ),
        headers=get_headers(),
    )

    assert create_response.status_code == 201

    template_id = create_response.json()["id"]

    response = api_client.get(
        f"/admin/prompts/{template_id}",
        headers=get_headers(),
    )

    assert response.status_code == 200
    assert response.json()["id"] == template_id


def test_patch_works(
    api_client: TestClient,
) -> None:
    create_response = api_client.post(
        "/admin/prompts",
        json=prompt_payload(
            prompt_status="patch",
            body="Original",
            variables=[],
        ),
        headers=get_headers(),
    )

    assert create_response.status_code == 201

    template_id = create_response.json()["id"]

    response = api_client.patch(
        f"/admin/prompts/{template_id}",
        json={
            "name": "Updated",
        },
        headers=get_headers(),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


def test_patch_agent_channel_and_language(
    api_client: TestClient,
) -> None:
    create_response = api_client.post(
        "/admin/prompts",
        json=prompt_payload(
            prompt_status="patch_lookup_fields",
            body="Original",
            variables=[],
        ),
        headers=get_headers(),
    )

    assert create_response.status_code == 201

    template_id = create_response.json()["id"]

    response = api_client.patch(
        f"/admin/prompts/{template_id}",
        json={
            "agent_type": "SentimentAgent",
            "channel": "email",
            "language": "ta",
        },
        headers=get_headers(),
    )

    assert response.status_code == 200

    result = response.json()

    assert result["agent_type"] == (
        "SentimentAgent"
    )

    assert result["channel"] == "email"
    assert result["language"] == "ta"


def test_delete_soft_deactivates_template(
    api_client: TestClient,
) -> None:
    create_response = api_client.post(
        "/admin/prompts",
        json=prompt_payload(
            prompt_status="delete",
            body="Delete test",
            variables=[],
        ),
        headers=get_headers(),
    )

    assert create_response.status_code == 201

    template_id = create_response.json()["id"]

    delete_response = api_client.delete(
        f"/admin/prompts/{template_id}",
        headers=get_headers(),
    )

    assert delete_response.status_code == 204

    get_response = api_client.get(
        f"/admin/prompts/{template_id}",
        headers=get_headers(),
    )

    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False


def test_cross_tenant_access_returns_404(
    api_client: TestClient,
) -> None:
    create_response = api_client.post(
        "/admin/prompts",
        json=prompt_payload(
            prompt_status="cross_tenant",
            body="Tenant one",
            variables=[],
        ),
        headers=get_headers(
            tenant="tenant_1"
        ),
    )

    assert create_response.status_code == 201

    template_id = create_response.json()["id"]

    response = api_client.get(
        f"/admin/prompts/{template_id}",
        headers=get_headers(
            tenant="tenant_2"
        ),
    )

    assert response.status_code == 404


# ==========================================================
# Validation and error tests
# ==========================================================


def test_invalid_name_returns_400(
    api_client: TestClient,
) -> None:
    payload = prompt_payload()
    payload["name"] = ""

    response = api_client.post(
        "/admin/prompts",
        json=payload,
        headers=get_headers(),
    )

    assert response.status_code == 400


def test_undeclared_variable_returns_400(
    api_client: TestClient,
) -> None:
    payload = prompt_payload(
        prompt_status="invalid_variables",
        body="{{ secret_value }}",
        variables=[],
    )

    response = api_client.post(
        "/admin/prompts",
        json=payload,
        headers=get_headers(),
    )

    assert response.status_code == 400

    # The raw prompt body must not be returned.
    assert "{{ secret_value }}" not in (
        response.text
    )


def test_invalid_lookup_enum_returns_400(
    api_client: TestClient,
) -> None:
    response = api_client.get(
        "/admin/prompts/lookup",
        params={
            "agent_type": "UnknownAgent",
            "channel": "sms",
            "language": "en",
            "status": "assigned",
        },
        headers=get_headers(),
    )

    assert response.status_code == 400


def test_persistence_error_returns_503(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_repository_error(
        *args,
        **kwargs,
    ):
        raise RepositoryError(
            "Sensitive database information"
        )

    monkeypatch.setattr(
        PromptTemplateRepository,
        "create",
        raise_repository_error,
    )

    response = api_client.post(
        "/admin/prompts",
        json=prompt_payload(
            prompt_status="persistence_error",
            body="Persistence",
            variables=[],
        ),
        headers=get_headers(),
    )

    assert response.status_code == 503

    assert (
        "Sensitive database information"
        not in response.text
    )