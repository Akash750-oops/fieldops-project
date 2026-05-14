import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime

from app.main import app
from app.database import Base, get_db
from app.models import Technician, Job

# Setup Test Database connection
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:kris123@localhost:5432/fieldops_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    db = TestingSessionLocal()
    # Clean up
    db.query(Job).delete()
    db.query(Technician).delete()
    db.commit()
    yield db
    db.close()

# --- Expected Test Cases ---

def test_assign_correct_technician(db_session):
    tech = Technician(technician_name="John Doe", technician_skill="AC Repair", technician_location="0,0", technician_status="AVAILABLE")
    db_session.add(tech)
    job = Job(customer_name="Test", location="0,0", issue_description="X", priority="HIGH", service_type="AC Repair", contact_number="1234567890", preferred_service_date=datetime.date.today(), required_skill="AC Repair")
    db_session.add(job)
    db_session.commit()
    
    response = client.post("/assign-job", json={
        "job_id": f"JOB{job.id}",
        "job_type": "AC Repair"
    })
    
    assert response.status_code == 200
    assert response.json()["message"] == "Technician assigned successfully"
    assert response.json()["assigned_technician"]["id"] == tech.technician_id

def test_skip_busy_technician(db_session):
    tech = Technician(technician_name="Busy", technician_skill="AC Repair", technician_location="0,0", technician_status="BUSY")
    db_session.add(tech)
    job = Job(customer_name="Test", location="0,0", issue_description="X", priority="HIGH", service_type="AC Repair", contact_number="1234567890", preferred_service_date=datetime.date.today(), required_skill="AC Repair")
    db_session.add(job)
    db_session.commit()
    
    response = client.post("/assign-job", json={"job_id": job.id, "job_type": "AC Repair"})
    assert response.status_code == 400
    assert "No available technicians found" in response.json()["error"]

def test_skip_offline_technician(db_session):
    tech = Technician(technician_name="Offline", technician_skill="AC Repair", technician_location="0,0", technician_status="OFFLINE")
    db_session.add(tech)
    job = Job(customer_name="Test", location="0,0", issue_description="X", priority="HIGH", service_type="AC Repair", contact_number="1234567890", preferred_service_date=datetime.date.today(), required_skill="AC Repair")
    db_session.add(job)
    db_session.commit()
    
    response = client.post("/assign-job", json={"job_id": job.id, "job_type": "AC Repair"})
    assert response.status_code == 400
    assert "No available technicians found" in response.json()["error"]

def test_workload_limit_validation(db_session):
    tech = Technician(technician_name="Limit", technician_skill="AC Repair", technician_location="0,0", technician_status="AVAILABLE", max_jobs=1)
    db_session.add(tech)
    job1 = Job(customer_name="T1", location="0,0", issue_description="X", priority="HIGH", service_type="AC Repair", contact_number="1234567890", preferred_service_date=datetime.date.today(), required_skill="AC Repair")
    db_session.add(job1)
    job2 = Job(customer_name="T2", location="0,0", issue_description="X", priority="HIGH", service_type="AC Repair", contact_number="1234567890", preferred_service_date=datetime.date.today(), required_skill="AC Repair")
    db_session.add(job2)
    db_session.commit()
    
    # 1st assignment
    client.post("/assign-job", json={"job_id": job1.id, "job_type": "AC Repair"})
    # 2nd assignment fails
    response = client.post("/assign-job", json={"job_id": job2.id, "job_type": "AC Repair"})
    assert response.status_code == 400
    assert "No available technicians found" in response.json()["error"]

def test_no_matching_skill_found(db_session):
    tech = Technician(technician_name="Plumber", technician_skill="Plumbing", technician_location="0,0", technician_status="AVAILABLE")
    db_session.add(tech)
    job = Job(customer_name="Test", location="0,0", issue_description="X", priority="HIGH", service_type="AC Repair", contact_number="1234567890", preferred_service_date=datetime.date.today(), required_skill="AC Repair")
    db_session.add(job)
    db_session.commit()
    
    response = client.post("/assign-job", json={"job_id": job.id, "job_type": "AC Repair"})
    assert response.status_code == 400
    assert "No available technicians found" in response.json()["error"]

def test_missing_job_id(db_session):
    response = client.post("/assign-job", json={"job_type": "AC Repair"})
    assert response.status_code == 400
    # The error message depends on pydantic/fastapi exception handler
    assert "error" in response.json()

def test_missing_job_type(db_session):
    job = Job(customer_name="T", location="0,0", issue_description="X", priority="HIGH", service_type="AC", contact_number="1234567890", preferred_service_date=datetime.date.today())
    db_session.add(job)
    db_session.commit()
    response = client.post("/assign-job", json={"job_id": job.id})
    assert response.status_code == 400
    assert "Either technician_id or job_type must be provided" in response.json()["error"]

def test_invalid_job_id(db_session):
    response = client.post("/assign-job", json={"job_id": 9999, "job_type": "AC Repair"})
    assert response.status_code == 404
    assert "Job not found" in response.json()["error"]

def test_database_updated_after_assignment(db_session):
    tech = Technician(technician_name="Update", technician_skill="AC Repair", technician_location="0,0", technician_status="AVAILABLE")
    db_session.add(tech)
    job = Job(customer_name="T", location="0,0", issue_description="X", priority="HIGH", service_type="AC Repair", contact_number="1234567890", preferred_service_date=datetime.date.today(), required_skill="AC Repair")
    db_session.add(job)
    db_session.commit()
    
    client.post("/assign-job", json={"job_id": job.id, "job_type": "AC Repair"})
    
    db_session.refresh(job)
    db_session.refresh(tech)
    assert job.assigned_technician_id == tech.technician_id
    assert job.status == "in progress"
    assert tech.current_jobs == 1

def test_api_response_status_code(db_session):
    tech = Technician(technician_name="S", technician_skill="AC Repair", technician_location="0,0", technician_status="AVAILABLE")
    db_session.add(tech)
    job = Job(customer_name="T", location="0,0", issue_description="X", priority="HIGH", service_type="AC Repair", contact_number="1234567890", preferred_service_date=datetime.date.today(), required_skill="AC Repair")
    db_session.add(job)
    db_session.commit()
    
    response = client.post("/assign-job", json={"job_id": job.id, "job_type": "AC Repair"})
    assert response.status_code == 200
    assert "Technician assigned successfully" in response.json()["message"]

def test_match_skill_status_code(db_session):
    tech = Technician(technician_name="S", technician_skill="AC Repair", technician_location="0,0", technician_status="AVAILABLE")
    db_session.add(tech)
    db_session.commit()
    response = client.get("/technicians/match-skill?job_type=AC Repair")
    assert response.status_code == 200
    assert len(response.json()) == 1
