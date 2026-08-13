import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from app.auth.dependencies import get_current_user, AuthenticatedUser
from app.auth.rbac import UserRole
from app.main import app
from app.models import Job, Technician, AuditEvent, DispatcherNotification, User
from app.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.redis_client import get_redis_client
from app.auth.jwt_handler import create_access_token

from fakeredis import FakeRedis


# ============================================================
# Test Database
# ============================================================

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# Fake Redis
# ============================================================

mock_redis = FakeRedis(decode_responses=True)


def override_get_redis():
    return mock_redis


# ============================================================
# Test Client
# ============================================================

client = TestClient(app)


# ============================================================
# Database Fixture
# ============================================================

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    mock_redis.flushall()

    yield db

    db.close()


# ============================================================
# Authentication Override
# ============================================================

async def override_get_current_user():
    return AuthenticatedUser(
        user_id="tech-123",
        tenant_id="tenant-1",
        role=UserRole.TECHNICIAN,
        jti="test-jti",
    )


@pytest.fixture(autouse=True)
def apply_overrides():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_redis_client] = override_get_redis

    yield

    app.dependency_overrides.clear()


# ============================================================
# 1. Successful rejection
# ============================================================

def test_reject_succeeds_with_valid_reason(setup_db):
    db = setup_db

    user = User(
        id="tech-123",
        email="tech123@test.com",
        password_hash="test-password",
        first_name="John",
        last_name="Doe",
        role="technician",
        tenant_id="tenant-1",
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    db.commit()

    access_token = create_access_token(
        user_id="tech-123",
        tenant_id="tenant-1",
        role="technician"
    )


    tech = Technician(
        tech_id="tech-123",
        technician_name="John Doe",
        technician_skill="Plumbing",
        technician_location="0,0",
        technician_status="BUSY",
        current_jobs=1,
        tenant_id="tenant-1",
    )


    db.add(tech)
    db.commit()
    db.refresh(tech)


    job = Job(
        customer_name="Alice",
        location="1,1",
        issue_description="Leak",
        priority="HIGH",
        service_type="Plumbing",
        contact_number="1234567890",
        preferred_service_date=datetime.now().date(),
        status="ASSIGNED",
        assigned_technician_id=tech.technician_id,
        tenant_id="tenant-1"
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    reason_text = "Customer is way too far away from me"

    response = client.post(
        f"/jobs/{job.id}/reject",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Tenant-ID": "tenant-1"
        },
        json={"reason": reason_text}
    )

    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "QUEUED"
    assert data["rejection"]["reason"] == reason_text
    assert data["cooldown"]["duration_seconds"] == 120
    assert data["re_dispatch"]["triggered"] is True

    # Verify DB state
    db.refresh(job)
    db.refresh(tech)

    assert job.status == "QUEUED"
    assert tech.current_jobs == 0
    assert tech.technician_status == "AVAILABLE"

    # Verify Redis cooldown
    assert mock_redis.exists(
        f"job:cooldown:{job.id}:tech-123"
    )

    # Verify Audit Event
    audit = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.tech_id == "tech-123",
            AuditEvent.event_type == "JOB_REJECTED",
        )
        .first()
    )

    assert audit is not None
    assert audit.reason == reason_text

    # Verify Dispatcher Notification
    notif = (
        db.query(DispatcherNotification)
        .filter(
            DispatcherNotification.tech_id == "tech-123"
        )
        .first()
    )

    assert notif is not None
    assert reason_text in notif.message


# ============================================================
# 2. Reason too short
# ============================================================

def test_reject_400_reason_too_short(setup_db):
    db = setup_db

    user = User(
        id="tech-123",
        email="tech123@test.com",
        password_hash="test-password",
        first_name="John",
        last_name="Doe",
        role="technician",
        tenant_id="tenant-1",
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    db.commit()

    access_token = create_access_token(
        user_id="tech-123",
        tenant_id="tenant-1",
        role="technician"
    )

    response = client.post(
        "/jobs/1/reject",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Tenant-ID": "tenant-1"
        },
        json={"reason": "short"}
    )

    assert response.status_code == 400


# ============================================================
# 3. Job not found
# ============================================================

def test_reject_404_job_not_found(setup_db):
    db = setup_db

    user = User(
        id="tech-123",
        email="tech123@test.com",
        password_hash="test-password",
        first_name="John",
        last_name="Doe",
        role="technician",
        tenant_id="tenant-1",
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    db.commit()

    access_token = create_access_token(
        user_id="tech-123",
        tenant_id="tenant-1",
        role="technician"
    )

    response = client.post(
        "/jobs/999/reject",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Tenant-ID": "tenant-1"
        },
        json={"reason": "Customer is way too far away from me"}
    )


    assert response.status_code == 404


# ============================================================
# 4. Wrong technician
# ============================================================

def test_reject_403_wrong_technician(setup_db):
    db = setup_db

    user = User(
        id="wrong-tech",
        email="wrongtech@test.com",
        password_hash="test-password",
        first_name="Wrong",
        last_name="Technician",
        role="technician",
        tenant_id="tenant-1",
        is_active=True,
        is_email_verified=True,
    )

    db.add(user)
    db.commit()

    access_token = create_access_token(
        user_id="wrong-tech",
        tenant_id="tenant-1",
        role="technician"
    )

    # Authenticated technician
    wrong_tech = Technician(
        tech_id="wrong-tech",
        technician_name="Wrong Technician",
        technician_skill="Plumbing",
        technician_location="0,0",
        technician_status="AVAILABLE",
        current_jobs=0,
        tenant_id="tenant-1"
    )

    db.add(wrong_tech)
    db.commit()
    db.refresh(wrong_tech)

    # Technician actually assigned to the job
    tech = Technician(
        tech_id="tech-123",
        technician_name="John",
        technician_skill="Plumbing",
        technician_location="0,0",
        technician_status="AVAILABLE",
        current_jobs=0,
        tenant_id="tenant-1"
    )

    db.add(tech)
    db.commit()
    db.refresh(tech)

    # Job is assigned to tech-123, NOT wrong-tech
    job = Job(
        customer_name="Alice",
        location="1,1",
        issue_description="Leak",
        priority="HIGH",
        service_type="Plumbing",
        contact_number="1234567890",
        preferred_service_date=datetime.now().date(),
        status="ASSIGNED",
        assigned_technician_id=tech.technician_id,
        tenant_id="tenant-1"
    )


    db.add(job)
    db.commit()
    db.refresh(job)

    # IMPORTANT:
    # The current authentication override returns tech-123.
    # Therefore the Authorization header itself cannot change
    # current_user to wrong-tech.
    #
    # To test the actual authorization logic, temporarily override
    # the dependency with wrong-tech for this request.

    async def override_wrong_technician():
        return AuthenticatedUser(
            user_id="wrong-tech",
            tenant_id="tenant-1",
            role=UserRole.TECHNICIAN,
            jti="wrong-tech-jti",
        )

    app.dependency_overrides[get_current_user] = override_wrong_technician

    db.refresh(job)

    response = client.post(
        f"/jobs/{job.id}/reject",
        headers={
            "Authorization": "Bearer wrong-tech",
            "X-Tenant-ID": "tenant-1",
        },
        json={
            "reason": "Customer is way too far away from me"
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Tenant-ID": "tenant-1"
        },
        json={"reason": "Customer is way too far away from me"}
    )

    print("STATUS:", response.status_code)
    print("BODY:", response.text)


    assert response.status_code == 403