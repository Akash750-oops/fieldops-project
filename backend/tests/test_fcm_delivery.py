import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi.testclient import TestClient
from fastapi import Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import factory
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import Base, get_db
from app import models
import firebase_admin.messaging as messaging

# 1. Test database setup using isolated SQLite in-memory
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
test_db_session = TestingSessionLocal()

# 2. Define Custom Firebase SDK Exceptions & Response Mocks for send_each_for_multicast
class UnregisteredError(Exception):
    pass

class InvalidArgumentError(Exception):
    pass

class MockSendResponse:
    def __init__(self, success=True, message_id=None, exception=None):
        self.success = success
        self.message_id = message_id or f"projects/fieldops/messages/{uuid.uuid4().hex}"
        self.exception = exception

class MockBatchResponse:
    def __init__(self, responses):
        self.responses = responses

# 3. Factory Boy definitions for test data
class TechnicianFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Technician
        sqlalchemy_session = test_db_session
        sqlalchemy_session_persistence = "commit"

    tech_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    tenant_id = "tenant-123"
    technician_name = factory.Faker('name')
    technician_skill = "HVAC"
    technician_location = "13.0,80.0"
    technician_status = "AVAILABLE"
    current_jobs = 0
    max_jobs = 5
    fcm_token = factory.LazyFunction(lambda: f"fcm_token_{uuid.uuid4().hex[:10]}")
    device_type = "android"
    phone_number = "+1234567890"

class JobFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Job
        sqlalchemy_session = test_db_session
        sqlalchemy_session_persistence = "commit"

    customer_name = factory.Faker('name')
    location = "13.0,80.0"
    issue_description = "HVAC system not cooling"
    priority = "HIGH"
    service_type = "HVAC"
    contact_number = "+1234567890"
    preferred_service_date = factory.LazyFunction(lambda: datetime.now(timezone.utc).date())
    status = "active"

class InAppNotificationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.InAppNotification
        sqlalchemy_session = test_db_session
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    tech_id = ""
    job_id = ""
    type = "job_assignment"
    title = "New Job"
    body = "New Job Assignment"
    status = "UNREAD"
    action_type = "deep_link"
    priority = "NORMAL"

# 4. Standard database and client fixtures
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    try:
        yield test_db_session
    finally:
        test_db_session.rollback()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers():
    def _headers(tenant_id="tenant-123", token="sample_token"):
        return {
            "X-Tenant-ID": tenant_id,
            "Authorization": f"Bearer {token}"
        }
    return _headers

@pytest.fixture(autouse=True)
def mock_asyncio_sleep(monkeypatch):
    """Bypasses sleep to speed up retry backoff tests"""
    async def mock_sleep(seconds):
        pass
    monkeypatch.setattr("asyncio.sleep", mock_sleep)

# Dynamic FastAPI route registration to simulate accepting a job
@pytest.fixture(scope="function", autouse=True)
def register_accept_route():
    paths = [r.path for r in app.routes]
    if "/v1/jobs/{job_id}/accept" not in paths:
        @app.post("/v1/jobs/{job_id}/accept")
        def mock_accept(job_id: str, db: Session = Depends(get_db)):
            job = db.query(models.Job).filter(models.Job.id == int(job_id)).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            job.status = "ACCEPTED"
            db.commit()
            return {"status": "success", "job_id": job_id, "status_code": "ACCEPTED"}

# 5. Firebase Cloud Messaging Integration Test Suite

def test_valid_android_token_delivery(client, db_session, auth_headers, monkeypatch):
    """
    Scenario: Notification delivered to valid Android token
    Setup: Valid Android FCM token
    Action: Send notification
    Assert: Delivery status "sent" in NotificationDelivery table and android payload configuration verified
    """
    tech = TechnicianFactory(device_type="android", fcm_token="valid_android_token_123")
    job = JobFactory()

    captured_message = []
    def mock_send(message):
        captured_message.append(message)
        return MockBatchResponse([MockSendResponse(success=True)])

    monkeypatch.setattr(messaging, "send_each_for_multicast", mock_send)

    payload = {
        "job_id": str(job.id),
        "tech_ids": [tech.tech_id]
    }
    
    response = client.post("/notifications/send-push", headers=auth_headers(tech.tenant_id), json=payload)
    assert response.status_code == 200
    
    # Assert fcm.py returned sent count of 1
    data = response.json()
    assert data["sent"] == 1
    assert data["failed"] == 0
    assert len(data["delivery_ids"]) == 1

    # Assert NotificationDelivery status is "delivered" (marked as delivered on successful handoff)
    delivery = db_session.query(models.NotificationDelivery).filter_by(id=data["delivery_ids"][0]).first()
    assert delivery is not None
    assert delivery.status == "delivered"
    assert delivery.tech_id == tech.tech_id

    # Assert Android payload configuration
    assert len(captured_message) == 1
    msg = captured_message[0]
    assert msg.tokens == ["valid_android_token_123"]
    assert msg.android is not None
    assert msg.android.priority == "high"
    assert msg.android.notification.channel_id == "job_assignments"
    assert msg.android.notification.sound == "default"


def test_valid_ios_token_delivery(client, db_session, auth_headers, monkeypatch):
    """
    Scenario: Notification delivered to valid iOS token
    Setup: Valid iOS FCM token
    Action: Send notification
    Assert: Delivery status "sent" and iOS/APNS configuration verified
    """
    tech = TechnicianFactory(device_type="ios", fcm_token="valid_ios_token_123")
    job = JobFactory()

    captured_message = []
    def mock_send(message):
        captured_message.append(message)
        return MockBatchResponse([MockSendResponse(success=True)])

    monkeypatch.setattr(messaging, "send_each_for_multicast", mock_send)

    payload = {
        "job_id": str(job.id),
        "tech_ids": [tech.tech_id]
    }
    
    response = client.post("/notifications/send-push", headers=auth_headers(tech.tenant_id), json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["sent"] == 1
    assert data["failed"] == 0

    # Assert NotificationDelivery status
    delivery = db_session.query(models.NotificationDelivery).filter_by(id=data["delivery_ids"][0]).first()
    assert delivery is not None
    assert delivery.status == "delivered"

    # Assert APNS payload configuration
    assert len(captured_message) == 1
    msg = captured_message[0]
    assert msg.tokens == ["valid_ios_token_123"]
    assert msg.apns is not None
    assert msg.apns.payload.aps.badge == 1
    assert msg.apns.payload.aps.sound == "default"
    assert msg.apns.payload.aps.category == "JOB_ASSIGNMENT"


def test_invalid_token_handling(client, db_session, auth_headers, monkeypatch):
    """
    Scenario: Notification not delivered to invalid token
    Setup: Invalid/expired token
    Action: Send notification (simulating UnregisteredError from FCM)
    Assert: Token removed from database, delivery marked failed
    """
    tech = TechnicianFactory(fcm_token="expired_token_abc")
    job = JobFactory()

    def mock_send(message):
        return MockBatchResponse([
            MockSendResponse(success=False, exception=UnregisteredError("App instance unregistered"))
        ])

    monkeypatch.setattr(messaging, "send_each_for_multicast", mock_send)

    payload = {
        "job_id": str(job.id),
        "tech_ids": [tech.tech_id]
    }
    
    response = client.post("/notifications/send-push", headers=auth_headers(tech.tenant_id), json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["sent"] == 0
    assert data["failed"] == 1

    # Assert invalid token was cleaned up
    db_session.refresh(tech)
    assert tech.fcm_token is None

    # Assert NotificationDelivery created with failed status
    delivery = db_session.query(models.NotificationDelivery).filter_by(id=data["delivery_ids"][0]).first()
    assert delivery is not None
    assert delivery.status == "failed"
    assert "App instance unregistered" in delivery.error_message


def test_click_opens_job_detail(client, db_session, auth_headers, monkeypatch):
    """
    Scenario: Click opens app to job detail page
    Setup: Notification with job_id
    Action: Click notification (extract deep link parameters from payload)
    Assert: Verify the data contains parameters for navigating directly to job details
    """
    tech = TechnicianFactory()
    job = JobFactory()

    captured_message = []
    def mock_send(message):
        captured_message.append(message)
        return MockBatchResponse([MockSendResponse(success=True)])

    monkeypatch.setattr(messaging, "send_each_for_multicast", mock_send)

    payload = {
        "job_id": str(job.id),
        "tech_ids": [tech.tech_id]
    }
    
    client.post("/notifications/send-push", headers=auth_headers(tech.tenant_id), json=payload)

    # Verify message data payload
    assert len(captured_message) == 1
    data_payload = captured_message[0].data
    assert data_payload["job_id"] == str(job.id)
    assert data_payload["type"] == "job_assignment"


def test_click_accept_action(client, db_session, auth_headers, monkeypatch):
    """
    Scenario: Click on accept button in notification
    Setup: Notification with accept_url
    Action: Click accept button (make HTTP request to the accept_url)
    Assert: Job status changes to ACCEPTED
    """
    tech = TechnicianFactory()
    job = JobFactory(status="active")

    captured_message = []
    def mock_send(message):
        captured_message.append(message)
        return MockBatchResponse([MockSendResponse(success=True)])

    monkeypatch.setattr(messaging, "send_each_for_multicast", mock_send)

    payload = {
        "job_id": str(job.id),
        "tech_ids": [tech.tech_id]
    }
    
    client.post("/notifications/send-push", headers=auth_headers(tech.tenant_id), json=payload)

    # Extract accept_url from payload
    assert len(captured_message) == 1
    accept_url = captured_message[0].data["accept_url"]
    
    # Parse the route path and invoke it to simulate click/accept action
    parsed = urlparse(accept_url)
    accept_path = parsed.path
    
    response = client.post(accept_path, headers=auth_headers(tech.tenant_id))
    assert response.status_code == 200
    assert response.json()["status_code"] == "ACCEPTED"

    # Assert job status changed to ACCEPTED in DB
    db_session.refresh(job)
    assert job.status == "ACCEPTED"


def test_background_notification(client, db_session, auth_headers, monkeypatch):
    """
    Scenario: Notification shown when app in background
    Setup: App in background (requires OS tray display)
    Action: Send notification
    Assert: Verify message contains BOTH 'notification' (for OS tray display) and 'data' blocks
    """
    tech = TechnicianFactory()
    job = JobFactory()

    captured_message = []
    def mock_send(message):
        captured_message.append(message)
        return MockBatchResponse([MockSendResponse(success=True)])

    monkeypatch.setattr(messaging, "send_each_for_multicast", mock_send)

    payload = {
        "job_id": str(job.id),
        "tech_ids": [tech.tech_id]
    }
    
    client.post("/notifications/send-push", headers=auth_headers(tech.tenant_id), json=payload)

    # Assert both notification & data sections are set
    assert len(captured_message) == 1
    msg = captured_message[0]
    assert msg.notification is not None
    assert msg.notification.title == "New Job Assignment"
    assert msg.data is not None
    assert msg.data["job_id"] == str(job.id)


def test_closed_app_notification(client, db_session, auth_headers, monkeypatch):
    """
    Scenario: Notification shown when app closed
    Setup: App closed (requires waking lock screen)
    Action: Send notification
    Assert: Verify Android priority is 'high' to display on lock screen immediately
    """
    tech = TechnicianFactory()
    job = JobFactory()

    captured_message = []
    def mock_send(message):
        captured_message.append(message)
        return MockBatchResponse([MockSendResponse(success=True)])

    monkeypatch.setattr(messaging, "send_each_for_multicast", mock_send)

    payload = {
        "job_id": str(job.id),
        "tech_ids": [tech.tech_id]
    }
    
    client.post("/notifications/send-push", headers=auth_headers(tech.tenant_id), json=payload)

    # Assert high priority settings are present to wake the device
    assert len(captured_message) == 1
    msg = captured_message[0]
    assert msg.android.priority == "high"


def test_badge_increment(client, db_session, auth_headers, monkeypatch):
    """
    Scenario: Badge count increments correctly
    Setup: Starting count = 2 unread in-app notifications
    Action: Send notification (dispatches a new in-app notification)
    Assert: Badge count increments to 3
    """
    tech = TechnicianFactory()
    
    # Setup: 2 unread notifications already in database
    InAppNotificationFactory(tech_id=tech.tech_id, status="UNREAD")
    InAppNotificationFactory(tech_id=tech.tech_id, status="UNREAD")

    # Verify count is 2
    count_before = db_session.query(models.InAppNotification).filter(
        models.InAppNotification.tech_id == tech.tech_id,
        models.InAppNotification.status == "UNREAD"
    ).count()
    assert count_before == 2

    # Action: Send new in-app notification to simulate delivery
    InAppNotificationFactory(tech_id=tech.tech_id, status="UNREAD")

    # Assert: Badge/unread count is now 3
    count_after = db_session.query(models.InAppNotification).filter(
        models.InAppNotification.tech_id == tech.tech_id,
        models.InAppNotification.status == "UNREAD"
    ).count()
    assert count_after == 3


def test_retry_on_failure(client, db_session, auth_headers, monkeypatch):
    """
    Scenario: Retry on transient failure
    Setup: FCM API returns transient 500 error
    Action: Send notification
    Assert: Retried 3 times, then marked failed on final exhaustion
    """
    tech = TechnicianFactory(fcm_token="transient_err_token")
    job = JobFactory()

    call_count = 0
    def mock_send(message):
        nonlocal call_count
        call_count += 1
        # Simulate transient error (e.g. Connection Error / 500)
        return MockBatchResponse([
            MockSendResponse(success=False, exception=Exception("Internal FCM Server Error"))
        ])

    monkeypatch.setattr(messaging, "send_each_for_multicast", mock_send)

    payload = {
        "job_id": str(job.id),
        "tech_ids": [tech.tech_id]
    }
    
    response = client.post("/notifications/send-push", headers=auth_headers(tech.tenant_id), json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["sent"] == 0
    assert data["failed"] == 1

    # Assert it was called up to 3 times (the max_retries configured in fcm.py)
    assert call_count == 3

    # Assert NotificationDelivery status is marked failed
    delivery = db_session.query(models.NotificationDelivery).filter_by(id=data["delivery_ids"][0]).first()
    assert delivery is not None
    assert delivery.status == "failed"
    assert "Internal FCM Server Error" in delivery.error_message
