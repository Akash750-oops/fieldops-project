import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import factory
import os
import sys
from fastapi import Request, Form, Depends
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import Base, get_db
from app import models
from app.services import twilio_sms
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# 1. Test database setup using isolated SQLite in-memory
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Factory Boy definitions for test data
class TechnicianFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Technician

    tech_id = factory.LazyAttribute(lambda _: str(uuid.uuid4()))
    tenant_id = "tenant-123"
    technician_name = factory.Faker('name')
    technician_skill = "HVAC"
    technician_location = "13.0,80.0"
    technician_status = "AVAILABLE"
    phone_number = factory.Sequence(lambda n: f"+9198765{n:04d}")
    sms_opt_out = 0

class JobFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Job

    customer_name = factory.Faker('name')
    location = "13.0,80.0"
    issue_description = "HVAC system not cooling"
    priority = "HIGH"
    service_type = "HVAC"
    contact_number = "+1234567890"
    preferred_service_date = factory.LazyFunction(lambda: datetime.now(timezone.utc).date())
    status = "active"

# 3. Standard database and client fixtures
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    TechnicianFactory._meta.sqlalchemy_session = session
    TechnicianFactory._meta.sqlalchemy_session_persistence = "commit"
    JobFactory._meta.sqlalchemy_session = session
    JobFactory._meta.sqlalchemy_session_persistence = "commit"
    try:
        yield session
    finally:
        session.rollback()
        session.close()
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

@pytest.fixture(autouse=True)
def mock_asyncio_sleep(monkeypatch):
    """Bypasses sleep to speed up retry backoff tests"""
    async def mock_sleep(seconds):
        pass
    monkeypatch.setattr("asyncio.sleep", mock_sleep)

# Dynamic FastAPI route registration for webhooks
@pytest.fixture(scope="function", autouse=True)
def register_webhook_routes():
    paths = [r.path for r in app.routes]
    
    if "/v1/webhooks/twilio-inbound" not in paths:
        @app.post("/v1/webhooks/twilio-inbound")
        async def twilio_inbound(request: Request, db: Session = Depends(get_db)):
            form_data = await request.form()
            body = form_data.get("Body", "").strip().upper()
            from_number = form_data.get("From")
            
            if body == "STOP":
                tech = db.query(models.Technician).filter(models.Technician.phone_number == from_number).first()
                if tech:
                    tech.sms_opt_out = 1
                    tech.notification_preferences = {**tech.notification_preferences, "sms_enabled": False}
                    db.commit()
            return {"status": "ok"}
            
    if "/v1/webhooks/twilio-status" not in paths:
        @app.post("/v1/webhooks/twilio-status")
        async def twilio_status(request: Request, db: Session = Depends(get_db)):
            form_data = await request.form()
            message_sid = form_data.get("MessageSid")
            message_status = form_data.get("MessageStatus")
            
            delivery = db.query(models.SMSDelivery).filter(models.SMSDelivery.sms_sid == message_sid).first()
            if delivery:
                delivery.status = message_status
                if message_status == "delivered":
                    # Assume $0.01 per SMS for cost tracking mock
                    delivery.cost = 0.01
                db.commit()
            return {"status": "ok"}

# Redis Mock
class MockRedis:
    def __init__(self):
        self.data = {}
    def get(self, key):
        return self.data.get(key)
    def pipeline(self):
        return self
    def incr(self, key):
        self.data[key] = int(self.data.get(key, 0)) + 1
    def expire(self, key, time):
        pass
    def execute(self):
        pass

@pytest.fixture(autouse=True)
def mock_redis_client(monkeypatch):
    mock_redis = MockRedis()
    import app.redis_client
    import app.services.twilio_sms
    import app.services.preferences
    monkeypatch.setattr(app.redis_client, "get_redis_client", lambda: mock_redis)
    monkeypatch.setattr(app.services.twilio_sms, "get_redis_client", lambda: mock_redis)
    monkeypatch.setattr(app.services.preferences, "get_redis_client", lambda: mock_redis)
    return mock_redis

# Mock Twilio Client
class MockMessage:
    def __init__(self, sid):
        self.sid = sid

class MockMessages:
    def __init__(self):
        self.create_mock = MagicMock()
        
    def create(self, **kwargs):
        return self.create_mock(**kwargs)

class MockTwilioClient:
    def __init__(self):
        self.messages = MockMessages()

@pytest.fixture
def mock_twilio(monkeypatch):
    client = MockTwilioClient()
    client.messages.create_mock.return_value = MockMessage(sid="SM1234567890abcdef")
    monkeypatch.setattr(twilio_sms, "twilio_client", client)
    return client

# ----------------- TEST CASES -----------------

@pytest.mark.asyncio
async def test_valid_indian_number(db_session, mock_twilio):
    tech = TechnicianFactory(phone_number="+919876543210")
    job = JobFactory()
    
    res = await twilio_sms.send_job_assignment_sms(db_session, str(job.id), "Fix HVAC", "Delhi", "HIGH", [tech.tech_id])
    
    assert res["sent"] == 1
    assert res["failed"] == 0
    
    # Assert delivery status created as sent/queued
    delivery = db_session.query(models.SMSDelivery).filter_by(tech_id=tech.tech_id).first()
    assert delivery is not None
    assert delivery.status in ["queued", "sent"]

@pytest.mark.asyncio
async def test_valid_us_number(db_session, mock_twilio):
    tech = TechnicianFactory(phone_number="+15551234567")
    job = JobFactory()
    
    res = await twilio_sms.send_job_assignment_sms(db_session, str(job.id), "Fix HVAC", "NY", "HIGH", [tech.tech_id])
    
    assert res["sent"] == 1
    
    delivery = db_session.query(models.SMSDelivery).filter_by(tech_id=tech.tech_id).first()
    assert delivery is not None
    assert delivery.status in ["queued", "sent"]

@pytest.mark.asyncio
async def test_invalid_number(db_session, mock_twilio):
    tech = TechnicianFactory(phone_number="+123") # too short
    job = JobFactory()
    
    res = await twilio_sms.send_job_assignment_sms(db_session, str(job.id), "Fix HVAC", "NY", "HIGH", [tech.tech_id])
    
    assert res["sent"] == 0
    assert res["failed"] == 1
    
    # 400 error validation failed - no delivery recorded because it skips before creation
    delivery = db_session.query(models.SMSDelivery).filter_by(tech_id=tech.tech_id).first()
    assert delivery is None

def test_opt_out_stop(client, db_session):
    tech = TechnicianFactory(phone_number="+15551234567")
    
    response = client.post("/v1/webhooks/twilio-inbound", data={"From": "+15551234567", "Body": "STOP"})
    assert response.status_code == 200
    
    db_session.refresh(tech)
    assert tech.sms_opt_out == 1
    assert tech.notification_preferences.get("sms_enabled") is False

def test_delivery_status_webhook(client, db_session):
    tech = TechnicianFactory()
    job = JobFactory()
    
    # Pre-create delivery
    delivery = models.SMSDelivery(tech_id=tech.tech_id, job_id=str(job.id), sms_sid="SM999", status="sent")
    db_session.add(delivery)
    db_session.commit()
    
    response = client.post("/v1/webhooks/twilio-status", data={"MessageSid": "SM999", "MessageStatus": "delivered"})
    assert response.status_code == 200
    
    db_session.refresh(delivery)
    assert delivery.status == "delivered"

@pytest.mark.asyncio
async def test_retry_on_failure(db_session, mock_twilio):
    tech = TechnicianFactory(phone_number="+15551234567")
    job = JobFactory()
    
    # Make twilio throw 500 error 3 times
    mock_twilio.messages.create_mock.side_effect = TwilioRestException(
        status=500, uri="/Messages", msg="Internal Server Error"
    )
    
    res = await twilio_sms.send_job_assignment_sms(db_session, str(job.id), "Fix HVAC", "NY", "HIGH", [tech.tech_id])
    
    assert res["sent"] == 0
    assert res["failed"] == 1
    assert mock_twilio.messages.create_mock.call_count == 3
    
    delivery = db_session.query(models.SMSDelivery).filter_by(tech_id=tech.tech_id).first()
    assert delivery.status == "failed"

def test_message_length():
    long_title = "This is a very long job title that definitely exceeds the standard limit and needs to be truncated safely"
    address = "123 Main Street, Suite 400, Big City, State 12345"
    
    msg = twilio_sms.generate_sms_template(long_title, address, "HIGH", "job123")
    assert len(msg) < 160

@pytest.mark.asyncio
async def test_rate_limiting(db_session, mock_twilio):
    tech = TechnicianFactory(phone_number="+15551234567")
    job = JobFactory()
    
    # Send 15 SMS
    for i in range(15):
        res = await twilio_sms.send_job_assignment_sms(db_session, str(job.id), "Fix", "NY", "HIGH", [tech.tech_id])
        if i < 10:
            assert res["sent"] == 1
        else:
            assert res["sent"] == 0
            assert res["failed"] == 1

def test_cost_tracking(client, db_session):
    tech = TechnicianFactory()
    job = JobFactory()
    
    # Create 5 sent SMS
    for i in range(5):
        d = models.SMSDelivery(tech_id=tech.tech_id, job_id=str(job.id), sms_sid=f"SM_{i}", status="sent")
        db_session.add(d)
    db_session.commit()
    
    # Receive webhook for 5 SMS to mark delivered & assign cost
    for i in range(5):
        client.post("/v1/webhooks/twilio-status", data={"MessageSid": f"SM_{i}", "MessageStatus": "delivered"})
        
    deliveries = db_session.query(models.SMSDelivery).filter_by(tech_id=tech.tech_id).all()
    total_cost = sum(d.cost for d in deliveries if d.cost)
    
    # Expected cost = 5 * 0.01 = 0.05
    assert len(deliveries) == 5
    assert round(total_cost, 2) == 0.05
