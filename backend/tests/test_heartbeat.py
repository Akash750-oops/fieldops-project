import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
import uuid
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
        current_jobs=0,
        max_jobs=5
    )
    db_session.add(tech)
    db_session.commit()
    db_session.refresh(tech)
    return tech

def test_heartbeat_valid(client, sample_tech, mock_redis):
    """Test valid heartbeat updates timestamp and redis cache"""
    headers = {
        "X-Tenant-ID": "tenant-123",
        "Authorization": "Bearer sample_token"
    }
    
    response = client.post(f"/technicians/{sample_tech.tech_id}/heartbeat", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["tech_id"] == sample_tech.tech_id
    assert data["status"] == "AVAILABLE"
    assert "last_ping" in data
    
    # Check Redis
    heartbeat_key = f"tech:heartbeat:tenant-123:{sample_tech.tech_id}"
    assert mock_redis.get(heartbeat_key) == "AVAILABLE"
    assert mock_redis.expires[heartbeat_key] == 60

def test_heartbeat_invalid_uuid(client):
    """Test invalid UUID returns 400"""
    headers = {
        "X-Tenant-ID": "tenant-123",
        "Authorization": "Bearer sample_token"
    }
    
    response = client.post("/technicians/invalid-uuid/heartbeat", headers=headers)
    assert response.status_code == 400
    assert "Invalid technician ID format" in response.json()["error"]

def test_heartbeat_non_existent_tech(client):
    """Test non-existent tech returns 404"""
    headers = {
        "X-Tenant-ID": "tenant-123",
        "Authorization": "Bearer sample_token"
    }
    random_id = str(uuid.uuid4())
    
    response = client.post(f"/technicians/{random_id}/heartbeat", headers=headers)
    assert response.status_code == 404

def test_heartbeat_cross_tenant(client, sample_tech):
    """Test cross-tenant access returns 403"""
    headers = {
        "X-Tenant-ID": "tenant-456", # Different tenant
        "Authorization": "Bearer sample_token"
    }
    
    response = client.post(f"/technicians/{sample_tech.tech_id}/heartbeat", headers=headers)
    assert response.status_code == 403

def test_heartbeat_rate_limiting(client, sample_tech, mock_redis):
    """Test rate limiting (max 1 per 30 seconds)"""
    headers = {
        "X-Tenant-ID": "tenant-123",
        "Authorization": "Bearer sample_token"
    }
    
    # First request should succeed
    response = client.post(f"/technicians/{sample_tech.tech_id}/heartbeat", headers=headers)
    assert response.status_code == 200
    
    # Second request should fail with 429 because rate limit key is set in mock_redis
    response2 = client.post(f"/technicians/{sample_tech.tech_id}/heartbeat", headers=headers)
    assert response2.status_code == 429
    
    # Clear the rate limit and it should succeed again
    mock_redis.data = {}
    response3 = client.post(f"/technicians/{sample_tech.tech_id}/heartbeat", headers=headers)
    assert response3.status_code == 200

def test_heartbeat_unauthorized(client, sample_tech):
    """Test unauthorized when Bearer token is missing"""
    headers = {
        "X-Tenant-ID": "tenant-123",
    }
    
    response = client.post(f"/technicians/{sample_tech.tech_id}/heartbeat", headers=headers)
    assert response.status_code == 401
