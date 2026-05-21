import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import factory
import fakeredis
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import Base, get_db
from app import models
from app.redis_client import get_redis_client

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
test_db_session = TestingSessionLocal()

# Factory Boy
class TechnicianFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.Technician
        sqlalchemy_session = test_db_session
        sqlalchemy_session_persistence = "commit"

    tech_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    tenant_id = "tenant-123"
    technician_name = factory.Faker('name')
    technician_skill = "General"
    technician_location = "HQ"
    technician_status = "AVAILABLE"
    current_jobs = 0
    max_jobs = 5

@pytest.fixture(scope="function")
def mock_redis():
    return fakeredis.FakeRedis(decode_responses=False)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    try:
        yield test_db_session
    finally:
        test_db_session.rollback()
        Base.metadata.drop_all(bind=engine)

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

@pytest.fixture
def auth_headers():
    def _headers(tenant_id="tenant-123", token="sample_token"):
        return {
            "X-Tenant-ID": tenant_id,
            "Authorization": f"Bearer {token}"
        }
    return _headers

def test_valid_heartbeat(client, db_session, auth_headers, mock_redis):
    # Valid heartbeat updates timestamp
    tech = TechnicianFactory()
    headers = auth_headers(tenant_id=tech.tenant_id)
    payload = {"last_lat": 13.0, "last_lng": 80.0}
    
    response = client.post(f"/technicians/{tech.tech_id}/heartbeat", headers=headers, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tech_id"] == tech.tech_id
    assert "last_ping" in data
    
    # Check cache
    cached = mock_redis.get(f"tech:availability:{tech.tenant_id}:{tech.tech_id}")
    assert cached is not None
    cached_data = json.loads(cached)
    assert cached_data["last_lat"] == 13.0

def test_invalid_uuid(client, auth_headers):
    # Invalid UUID returns 400
    headers = auth_headers()
    response = client.post("/technicians/not-a-uuid/heartbeat", headers=headers, json={})
    assert response.status_code == 400

def test_nonexistent_tech(client, auth_headers):
    # Non-existent tech returns 404
    headers = auth_headers()
    fake_id = str(uuid.uuid4())
    response = client.post(f"/technicians/{fake_id}/heartbeat", headers=headers, json={})
    assert response.status_code == 404

def test_cross_tenant(client, db_session, auth_headers):
    # Cross-tenant access returns 403
    tech = TechnicianFactory(tenant_id="tenant-A")
    headers = auth_headers(tenant_id="tenant-B")
    response = client.post(f"/technicians/{tech.tech_id}/heartbeat", headers=headers, json={})
    assert response.status_code == 403

def test_unauthorized(client, db_session):
    # Missing auth returns 401
    tech = TechnicianFactory()
    headers = {"X-Tenant-ID": tech.tenant_id} # Missing Authorization
    response = client.post(f"/technicians/{tech.tech_id}/heartbeat", headers=headers, json={})
    assert response.status_code == 401

def test_rate_limit(client, db_session, auth_headers, mock_redis):
    # Rate limit exceeded returns 429
    tech = TechnicianFactory()
    headers = auth_headers(tenant_id=tech.tenant_id)
    
    # First request
    r1 = client.post(f"/technicians/{tech.tech_id}/heartbeat", headers=headers, json={})
    assert r1.status_code == 200
    
    # Second request immediately
    r2 = client.post(f"/technicians/{tech.tech_id}/heartbeat", headers=headers, json={})
    assert r2.status_code == 429

def test_redis_failure_fallback(client, db_session, auth_headers, monkeypatch):
    # Redis failure falls back to DB
    class FailingRedis:
        def get(self, key):
            raise Exception("Redis connection error")
        def setex(self, key, time, value):
            raise Exception("Redis connection error")
            
    app.dependency_overrides[get_redis_client] = lambda: FailingRedis()
    
    tech = TechnicianFactory()
    headers = auth_headers(tenant_id=tech.tenant_id)
    payload = {"last_lat": 13.0, "last_lng": 80.0}
    
    # Heartbeat shouldn't fail even if Redis is down
    response = client.post(f"/technicians/{tech.tech_id}/heartbeat", headers=headers, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "last_ping" in data
    
    # Check DB updated
    db_tech = db_session.query(models.Technician).filter(models.Technician.tech_id == tech.tech_id).first()
    assert db_tech.last_ping is not None
    app.dependency_overrides.clear()

import concurrent.futures

def test_concurrent_heartbeats(client, db_session, auth_headers, mock_redis):
    # Concurrent heartbeats handled
    tech = TechnicianFactory()
    headers = auth_headers(tenant_id=tech.tenant_id)
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = override_get_db

    def make_request():
        return client.post(
            f"/technicians/{tech.tech_id}/heartbeat", 
            headers=headers, 
            json={"last_lat": 1.0, "last_lng": 1.0}
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    app.dependency_overrides.clear()
    
    # Only one should succeed (200), rest 429 due to rate limiting
    status_codes = [r.status_code for r in responses]
    assert status_codes.count(200) == 1
    assert status_codes.count(429) == 4

def test_performance_100rps(client, db_session, auth_headers):
    # Performance test: P95 <100ms
    # We will simulate 100 requests to different techs (to avoid rate limit)
    
    techs = [TechnicianFactory() for _ in range(100)]
    latencies = []
    
    for tech in techs:
        headers = auth_headers(tenant_id=tech.tenant_id)
        start_time = time.time()
        response = client.post(f"/technicians/{tech.tech_id}/heartbeat", headers=headers, json={"last_lat": 1, "last_lng": 1})
        latencies.append((time.time() - start_time) * 1000)
        assert response.status_code == 200
        
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95 < 100, f"P95 latency {p95}ms exceeds 100ms"
