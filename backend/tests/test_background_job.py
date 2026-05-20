import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import Base
from app import models
from app.worker import check_technician_heartbeats

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_background_job.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class MockRedis:
    def __init__(self):
        self.data = {}
        self.expires = {}

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, time, value):
        self.data[key] = value
        self.expires[key] = time
        return True

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            if key in self.expires:
                del self.expires[key]
            return True
        return False

    def incr(self, key, amount=1):
        val = int(self.data.get(key, 0)) + amount
        self.data[key] = str(val)
        return val

    def expire(self, key, time):
        self.expires[key] = time
        return True

@pytest.fixture(scope="function")
def mock_redis():
    return MockRedis()

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def mock_worker_deps(monkeypatch, db_session, mock_redis):
    # Make db_session.close a no-op so the worker doesn't close our test session
    monkeypatch.setattr(db_session, "close", lambda: None)
    # Monkeypatch the worker's DB session and Redis client to use the test fixtures
    monkeypatch.setattr("app.worker.SessionLocal", lambda: db_session)
    monkeypatch.setattr("app.worker.get_redis_client", lambda: mock_redis)

def test_heartbeat_offline_trigger(db_session, mock_redis):
    """Test background job marks tech OFFLINE after 120s without heartbeat"""
    now = datetime.now(timezone.utc)
    
    # Tech with ping 130s ago -> should become OFFLINE
    tech_old = models.Technician(
        tech_id=str(uuid.uuid4()),
        tenant_id="tenant-1",
        technician_name="Old Ping",
        technician_skill="Support",
        technician_location="Lab",
        technician_status="AVAILABLE",
        last_ping=now - timedelta(seconds=130),
        current_jobs=0
    )
    
    # Tech with ping 50s ago -> should remain AVAILABLE
    tech_recent = models.Technician(
        tech_id=str(uuid.uuid4()),
        tenant_id="tenant-1",
        technician_name="Recent Ping",
        technician_skill="Support",
        technician_location="Lab",
        technician_status="AVAILABLE",
        last_ping=now - timedelta(seconds=50),
        current_jobs=0
    )
    
    db_session.add_all([tech_old, tech_recent])
    db_session.commit()
    
    # Pre-populate Redis for tech_old
    mock_redis.setex(f"tech:availability:tenant-1:{tech_old.tech_id}", 60, "AVAILABLE")
    
    # Run the background job
    check_technician_heartbeats()
    
    # Refresh techs
    db_session.refresh(tech_old)
    db_session.refresh(tech_recent)
    
    # Assert tech_old went offline and Redis cache got cleared
    assert tech_old.technician_status == "OFFLINE"
    assert mock_redis.get(f"tech:availability:tenant-1:{tech_old.tech_id}") is None
    
    # Assert tech_recent is still AVAILABLE
    assert tech_recent.technician_status == "AVAILABLE"
    
    # Check audit log
    audit = db_session.query(models.AuditEvent).filter(models.AuditEvent.tech_id == tech_old.tech_id).first()
    assert audit is not None
    assert audit.old_status == "AVAILABLE"
    assert audit.new_status == "OFFLINE"

def test_break_status_preserved(db_session):
    """Test that a technician with ON_BREAK status is preserved"""
    now = datetime.now(timezone.utc)
    
    tech_break = models.Technician(
        tech_id=str(uuid.uuid4()),
        tenant_id="tenant-1",
        technician_name="On Break Tech",
        technician_skill="Support",
        technician_location="Breakroom",
        technician_status="ON_BREAK",
        last_ping=now - timedelta(seconds=130),
        current_jobs=0
    )
    
    db_session.add(tech_break)
    db_session.commit()
    
    check_technician_heartbeats()
    db_session.refresh(tech_break)
    
    # Status should remain ON_BREAK since query only processes AVAILABLE / BUSY
    assert tech_break.technician_status == "ON_BREAK"

def test_busy_preservation_with_active_jobs(db_session):
    """Test that a BUSY tech with active jobs remains BUSY but triggers dispatcher notification"""
    now = datetime.now(timezone.utc)
    
    tech_busy = models.Technician(
        tech_id=str(uuid.uuid4()),
        tenant_id="tenant-1",
        technician_name="Busy Tech",
        technician_skill="Support",
        technician_location="Field",
        technician_status="BUSY",
        last_ping=now - timedelta(seconds=130),
        current_jobs=1
    )
    
    db_session.add(tech_busy)
    db_session.commit()
    
    check_technician_heartbeats()
    db_session.refresh(tech_busy)
    
    # Status MUST remain BUSY
    assert tech_busy.technician_status == "BUSY"
    
    # Check that dispatcher notification was created
    notification = db_session.query(models.DispatcherNotification).filter(
        models.DispatcherNotification.tech_id == tech_busy.tech_id
    ).first()
    assert notification is not None
    assert "missed heartbeat but has active jobs" in notification.message

def test_audit_log_immutability(db_session):
    """Test that audit log entries cannot be modified or deleted"""
    audit = models.AuditEvent(
        tech_id=str(uuid.uuid4()),
        tenant_id="tenant-1",
        event_type="STATUS_CHANGE",
        old_status="AVAILABLE",
        new_status="OFFLINE"
    )
    db_session.add(audit)
    db_session.commit()
    
    # Attempt to modify
    audit.new_status = "AVAILABLE"
    with pytest.raises(ValueError, match="AuditEvent is immutable"):
        db_session.commit()
        
    db_session.rollback()
    
    # Attempt to delete
    db_session.delete(audit)
    with pytest.raises(ValueError, match="AuditEvent is immutable"):
        db_session.commit()

def test_mass_offline_alerting(db_session, mock_redis, caplog):
    """Test that mass offline events (> 5) trigger CRITICAL alerts"""
    now = datetime.now(timezone.utc)
    
    for i in range(6):
        tech = models.Technician(
            tech_id=str(uuid.uuid4()),
            tenant_id="tenant-1",
            technician_name=f"Tech {i}",
            technician_skill="Support",
            technician_location="Lab",
            technician_status="AVAILABLE",
            last_ping=now - timedelta(seconds=130),
            current_jobs=0
        )
        db_session.add(tech)
        
    db_session.commit()
    
    # Run the worker and capture log
    import logging
    with caplog.at_level(logging.CRITICAL):
        check_technician_heartbeats()
        
    assert any("Mass OFFLINE event detected" in record.message for record in caplog.records)
    
    # Verify hourly offline metrics count in Redis
    hour_str = now.strftime("%Y-%m-%d-%H")
    metric_key = f"metrics:offline_events:{hour_str}"
    assert int(mock_redis.get(metric_key)) == 6
