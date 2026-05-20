import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
import uuid
import json
from datetime import datetime, timezone

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import Base, get_db
from app import models
from app.redis_client import get_redis_client

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_heartbeat.db"
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

@pytest.fixture(scope="function")
def client(db_session, mock_redis):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    def override_get_redis_client():
        return mock_redis
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis_client
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def sample_tech(db_session):
    tech = models.Technician(
        tech_id=str(uuid.uuid4()),
        tenant_id="tenant-123",
        technician_name="Heartbeat Tester",
        technician_skill="Testing",
        technician_location="Test Lab",
        technician_status="AVAILABLE",
        current_jobs=2,
        max_jobs=5
    )
    db_session.add(tech)
    db_session.commit()
    db_session.refresh(tech)
    return tech

def test_heartbeat_valid(client, sample_tech, mock_redis):
    """Test valid heartbeat updates timestamp and redis cache JSON"""
    headers = {
        "X-Tenant-ID": "tenant-123",
        "Authorization": "Bearer sample_token"
    }
    payload = {
        "last_lat": 13.0827,
        "last_lng": 80.2707
    }
    
    response = client.post(f"/technicians/{sample_tech.tech_id}/heartbeat", headers=headers, json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["tech_id"] == sample_tech.tech_id
    assert data["status"] == "AVAILABLE"
    assert "last_ping" in data
    assert data["active_jobs"] == 2
    assert data["last_lat"] == 13.0827
    assert data["last_lng"] == 80.2707
    
    # Check Redis
    heartbeat_key = f"tech:availability:tenant-123:{sample_tech.tech_id}"
    cached_raw = mock_redis.get(heartbeat_key)
    assert cached_raw is not None
    
    cached_json = json.loads(cached_raw)
    assert cached_json["tech_id"] == sample_tech.tech_id
    assert cached_json["last_lat"] == 13.0827
    assert mock_redis.expires[heartbeat_key] == 60

def test_availability_cache_hit(client, sample_tech, mock_redis):
    """Test cache read latency logic (hit)"""
    headers = {
        "X-Tenant-ID": "tenant-123",
        "Authorization": "Bearer sample_token"
    }
    
    # Pre-populate Redis
    heartbeat_key = f"tech:availability:tenant-123:{sample_tech.tech_id}"
    cache_data = {
        "tech_id": sample_tech.tech_id,
        "status": "AVAILABLE",
        "last_ping": "2026-05-19T10:30:00Z",
        "active_jobs": 2,
        "last_lat": 12.0,
        "last_lng": 80.0
    }
    mock_redis.setex(heartbeat_key, 60, json.dumps(cache_data))
    
    response = client.get(f"/technicians/{sample_tech.tech_id}/availability", headers=headers)
    assert response.status_code == 200
    assert response.json()["last_lat"] == 12.0

def test_availability_cache_miss_fallback(client, sample_tech, mock_redis):
    """Test cache read (miss/fallback to DB)"""
    headers = {
        "X-Tenant-ID": "tenant-123",
        "Authorization": "Bearer sample_token"
    }
    
    # Ensure Redis is empty
    heartbeat_key = f"tech:availability:tenant-123:{sample_tech.tech_id}"
    mock_redis.delete(heartbeat_key)
    
    response = client.get(f"/technicians/{sample_tech.tech_id}/availability", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["tech_id"] == sample_tech.tech_id
    assert data["status"] == "AVAILABLE"
    # Fallback to DB doesn't have lat/lng
    assert data["last_lat"] is None

def test_cache_invalidation(client, sample_tech, mock_redis):
    """Test cache invalidation endpoint"""
    headers = {
        "X-Tenant-ID": "tenant-123",
        "Authorization": "Bearer sample_token"
    }
    
    # Pre-populate Redis
    heartbeat_key = f"tech:availability:tenant-123:{sample_tech.tech_id}"
    mock_redis.setex(heartbeat_key, 60, '{"status": "BUSY"}')
    assert mock_redis.get(heartbeat_key) is not None
    
    # Invalidate cache
    response = client.post(f"/technicians/{sample_tech.tech_id}/invalidate-cache", headers=headers)
    assert response.status_code == 200
    
    # Verify cache is empty
    assert mock_redis.get(heartbeat_key) is None

def test_heartbeat_invalid_uuid(client):
    headers = {
        "X-Tenant-ID": "tenant-123",
        "Authorization": "Bearer sample_token"
    }
    response = client.post("/technicians/invalid-uuid/heartbeat", headers=headers)
    assert response.status_code == 400

def test_heartbeat_rate_limiting(client, sample_tech, mock_redis):
    headers = {
        "X-Tenant-ID": "tenant-123",
        "Authorization": "Bearer sample_token"
    }
    
    response = client.post(f"/technicians/{sample_tech.tech_id}/heartbeat", headers=headers)
    assert response.status_code == 200
    
    response2 = client.post(f"/technicians/{sample_tech.tech_id}/heartbeat", headers=headers)
    assert response2.status_code == 429
