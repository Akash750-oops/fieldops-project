import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import Base, get_db
from app import models

# Test database setup
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:kris123@localhost:5432/fieldops_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

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

@pytest.fixture(scope="function")
def sample_tech(db_session):
    tech = models.Technician(
        technician_name="Availability Tester",
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

def test_update_status_available(client, sample_tech):
    """Verify AVAILABLE status update"""
    response = client.put("/technicians/update-status", json={
        "technician_id": sample_tech.technician_id,
        "status": "AVAILABLE"
    })
    assert response.status_code == 200
    assert response.json()["technician_status"] == "AVAILABLE"

def test_update_status_busy(client, sample_tech):
    """Verify BUSY status update"""
    response = client.put("/technicians/update-status", json={
        "technician_id": sample_tech.technician_id,
        "status": "BUSY"
    })
    assert response.status_code == 200
    assert response.json()["technician_status"] == "BUSY"

def test_update_status_offline(client, sample_tech):
    """Verify OFFLINE status update"""
    response = client.put("/technicians/update-status", json={
        "technician_id": sample_tech.technician_id,
        "status": "OFFLINE"
    })
    assert response.status_code == 200
    assert response.json()["technician_status"] == "OFFLINE"

def test_invalid_status_rejection(client, sample_tech):
    """Verify invalid status rejection"""
    response = client.put("/technicians/update-status", json={
        "technician_id": sample_tech.technician_id,
        "status": "VACATION"
    })
    assert response.status_code == 400 # Custom handler in main.py returns 400

def test_assignment_reflects_status_changes(client, db_session, sample_tech):
    """Verify assignment reflects status changes"""
    # Create a job that matches the tech's skill
    job = models.Job(
        customer_name="Job Customer",
        location="Lab",
        issue_description="Test issue",
        priority="HIGH",
        service_type="Testing",
        contact_number="1234567890",
        preferred_service_date="2026-05-14",
        required_skill="Testing",
        status="active"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # 1. Update tech to BUSY
    client.put("/technicians/update-status", json={
        "technician_id": sample_tech.technician_id,
        "status": "BUSY"
    })

    # 2. Try to assign the job to this tech
    response = client.post("/assign-technician", json={
        "job_id": job.id,
        "technician_id": sample_tech.technician_id
    })
    assert response.status_code == 400
    assert "unavailable" in response.json()["error"].lower()

    # 3. Update tech to AVAILABLE
    client.put("/technicians/update-status", json={
        "technician_id": sample_tech.technician_id,
        "status": "AVAILABLE"
    })

    # 4. Try to assign again (should succeed)
    response = client.post("/assign-technician", json={
        "job_id": job.id,
        "technician_id": sample_tech.technician_id
    })
    assert response.status_code == 200
    assert response.json()["assigned_technician"]["name"] == sample_tech.technician_name

def test_unavailable_technicians_are_rejected(client, db_session, sample_tech):
    """Verify OFFLINE technicians are rejected for assignment"""
    job = models.Job(
        customer_name="Job Customer 2",
        location="Lab",
        issue_description="Test issue 2",
        priority="LOW",
        service_type="Testing",
        contact_number="1234567890",
        preferred_service_date="2026-05-14",
        required_skill="Testing",
        status="active"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # Set tech to OFFLINE
    client.put("/technicians/update-status", json={
        "technician_id": sample_tech.technician_id,
        "status": "OFFLINE"
    })

    # Try manual assignment
    response = client.post("/assign-technician", json={
        "job_id": job.id,
        "technician_id": sample_tech.technician_id
    })
    assert response.status_code == 400
    assert "offline" in response.json()["error"].lower()

def test_database_updates_correctly(client, db_session, sample_tech):
    """Verify status update is persisted in the database"""
    client.put("/technicians/update-status", json={
        "technician_id": sample_tech.technician_id,
        "status": "OFFLINE"
    })
    
    # Query database directly to verify persistence
    updated_tech = db_session.query(models.Technician).filter(models.Technician.technician_id == sample_tech.technician_id).first()
    assert updated_tech.technician_status == "OFFLINE"

def test_get_available_technicians_filters_correctly(client, db_session, sample_tech):
    """Verify GET /technicians/available returns only AVAILABLE techs and skips BUSY/OFFLINE"""
    # sample_tech is AVAILABLE initially
    
    # Create a BUSY tech
    busy_tech = models.Technician(
        technician_name="Busy Tech",
        technician_skill="Testing",
        technician_location="Lab",
        technician_status="BUSY",
        current_jobs=1,
        max_jobs=5
    )
    # Create an OFFLINE tech
    offline_tech = models.Technician(
        technician_name="Offline Tech",
        technician_skill="Testing",
        technician_location="Lab",
        technician_status="OFFLINE",
        current_jobs=0,
        max_jobs=5
    )
    db_session.add(busy_tech)
    db_session.add(offline_tech)
    db_session.commit()
    
    response = client.get("/technicians/available")
    assert response.status_code == 200
    techs = response.json()
    
    # Ensure only AVAILABLE tech is returned
    tech_names = [t["technician"] for t in techs]
    assert sample_tech.technician_name in tech_names
    assert "Busy Tech" not in tech_names
    assert "Offline Tech" not in tech_names

def test_no_technician_available_condition(client, db_session, sample_tech):
    """Verify empty list or specific response when no one is available"""
    # Change sample_tech to BUSY so no one is AVAILABLE
    client.put("/technicians/update-status", json={
        "technician_id": sample_tech.technician_id,
        "status": "BUSY"
    })
    
    response = client.get("/technicians/available")
    assert response.status_code == 200
    techs = response.json()
    
    assert len(techs) == 0
