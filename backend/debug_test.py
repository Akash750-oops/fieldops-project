import sys
import os
import asyncio
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app.database import Base
from app import models
from app.services import twilio_sms

# Setup SQLite DB in memory
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = TestingSessionLocal()

# Setup tables
Base.metadata.create_all(bind=engine)

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
        return self
    def expire(self, key, time):
        return self
    def execute(self):
        pass

mock_redis = MockRedis()
import app.services.twilio_sms as ts
ts.get_redis_client = lambda: mock_redis

# Mock Twilio Client
class MockMessage:
    def __init__(self, sid):
        self.sid = sid

class MockMessages:
    def create(self, **kwargs):
        return MockMessage(sid="SM123")

class MockTwilioClient:
    def __init__(self):
        self.messages = MockMessages()

ts.twilio_client = MockTwilioClient()

# Create tech and job
tech = models.Technician(
    tech_id=str(uuid.uuid4()),
    technician_name="John Doe",
    technician_skill="HVAC",
    technician_location="13.0,80.0",
    phone_number="+15551234567"
)
db.add(tech)

job = models.Job(
    customer_name="Test Customer",
    location="13.0,80.0",
    issue_description="Test HVAC",
    priority="HIGH",
    service_type="HVAC",
    contact_number="+1234567890",
    preferred_service_date=ts.datetime.now(ts.timezone.utc).date() if hasattr(ts, 'datetime') else None,
    status="active"
)
import datetime
job.preferred_service_date = datetime.date.today()
db.add(job)
db.commit()

async def main():
    print("Starting loop of 15 sends...")
    for i in range(15):
        print(f"Iteration {i} start")
        res = await ts.send_job_assignment_sms(db, str(job.id), "Fix", "NY", "HIGH", [tech.tech_id])
        print(f"Iteration {i} end: {res}")

asyncio.run(main())
