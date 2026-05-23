import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.routes.jobs import router
from app.database import get_db
from app.models import Job, Technician
from app.routes.dispatch import verify_jwt_token
from app.redis_client import get_redis_client
from unittest.mock import MagicMock

app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Mocks
mock_redis = MagicMock()
mock_redis.incr.return_value = 1
mock_redis.get.return_value = None

def override_get_redis_client():
    return mock_redis

def override_verify_jwt_token():
    return "Bearer valid"

# Mock DB Session
def override_get_db():
    db = MagicMock()
    
    # Setup test data
    job = Job(id=1, status="QUEUED", service_type="HVAC", location="12.9716,77.5946", required_skill="HVAC_CERT")
    
    tech1 = Technician(
        technician_id=1,
        tech_id="t1",
        tenant_id="test_tenant",
        technician_name="Alice",
        technician_status="AVAILABLE",
        technician_skill="HVAC_CERT, ELEC_LV",
        technician_location="12.9716,77.5946"
    )
    
    tech2 = Technician(
        technician_id=2,
        tech_id="t2",
        tenant_id="test_tenant",
        technician_name="Bob",
        technician_status="AVAILABLE",
        technician_skill="PLUMBING",
        technician_location="12.9716,77.5946"
    )
    
    def mock_query(model):
        m = MagicMock()
        if model == Job:
            m.filter.return_value.first.return_value = job
        elif model == Technician:
            m.filter.return_value.all.return_value = [tech1, tech2]
        return m
        
    db.query = mock_query
    yield db

app.dependency_overrides[get_redis_client] = override_get_redis_client
app.dependency_overrides[verify_jwt_token] = override_verify_jwt_token
app.dependency_overrides[get_db] = override_get_db


def test_planning_endpoint_success():
    mock_redis.get.return_value = None
    mock_redis.incr.return_value = 1
    
    response = client.post(
        "/jobs/1/plan",
        headers={"X-Tenant-ID": "test_tenant", "Authorization": "Bearer token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "1"
    assert data["status"] == "QUEUED"
    
    # Alice should be ranked, Bob disqualified
    ranked = data["ranked_technicians"]
    disqualified = data["disqualified_technicians"]
    
    assert len(ranked) == 1
    assert ranked[0]["name"] == "Alice"
    assert ranked[0]["is_top_3"] == True
    
    assert len(disqualified) == 1
    assert disqualified[0]["name"] == "Bob"
    assert disqualified[0]["reason"] == "missing_skills"

def test_planning_endpoint_rate_limit():
    mock_redis.incr.return_value = 11 # Exceeds limit of 10
    
    response = client.post(
        "/jobs/1/plan",
        headers={"X-Tenant-ID": "test_tenant", "Authorization": "Bearer token"}
    )
    
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded"

def test_planning_endpoint_job_not_found():
    def db_job_not_found():
        db = MagicMock()
        def mock_query(model):
            m = MagicMock()
            if model == Job:
                m.filter.return_value.first.return_value = None
            return m
        db.query = mock_query
        yield db
        
    app.dependency_overrides[get_db] = db_job_not_found
    mock_redis.incr.return_value = 1
    
    response = client.post(
        "/jobs/99/plan",
        headers={"X-Tenant-ID": "test_tenant", "Authorization": "Bearer token"}
    )
    
    assert response.status_code == 404
    
    # Restore DB mock
    app.dependency_overrides[get_db] = override_get_db

def test_planning_endpoint_wrong_status():
    def db_wrong_status():
        db = MagicMock()
        job = Job(id=1, status="COMPLETED")
        def mock_query(model):
            m = MagicMock()
            if model == Job:
                m.filter.return_value.first.return_value = job
            return m
        db.query = mock_query
        yield db
        
    app.dependency_overrides[get_db] = db_wrong_status
    
    response = client.post(
        "/jobs/1/plan",
        headers={"X-Tenant-ID": "test_tenant", "Authorization": "Bearer token"}
    )
    
    assert response.status_code == 400
    assert "QUEUED" in response.json()["detail"]
    
    # Restore DB mock
    app.dependency_overrides[get_db] = override_get_db
