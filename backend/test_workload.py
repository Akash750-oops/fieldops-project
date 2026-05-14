import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import Technician, Job
import datetime

# Use a separate test database if possible, but for this environment, 
# we'll use the existing one or a temporary sqlite if it's easier.
# However, the project is configured for Postgres. 
# I'll use the existing DB but clean up after.

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Elavenil2005%40%40@localhost:5432/fieldops_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_workload_limitation():
    # 1. Setup: Create a technician with max_jobs=2
    db = TestingSessionLocal()
    # Clean up first
    db.query(Job).delete()
    db.query(Technician).delete()
    db.commit()

    tech_name = "Test Tech"
    tech_skill = "Repair"
    
    response = client.post("/technicians/", json={
        "technician_name": tech_name,
        "technician_skill": tech_skill,
        "technician_location": "10,10",
        "technician_status": "AVAILABLE"
    })
    assert response.status_code == 200
    tech_id = response.json()["technician_id"]
    
    # Update tech to have max_jobs=2 (via DB since we don't have a PUT yet or it defaults to 5)
    tech = db.query(Technician).filter(Technician.technician_id == tech_id).first()
    tech.max_jobs = 2
    db.commit()

    # 2. Setup: Create 3 jobs
    job_ids = []
    for i in range(3):
        resp = client.post("/jobs/", json={
            "customer_name": f"Customer {i}",
            "location": "11,11",
            "issue_description": "Broken pipe",
            "priority": "HIGH",
            "service_type": "Repair",
            "contact_number": "1234567890",
            "preferred_service_date": str(datetime.date.today()),
            "required_skill": tech_skill
        })
        assert resp.status_code == 201
        job_ids.append(resp.json()["id"])

    # 3. Assign 1st Job
    resp = client.post("/assign-job", json={"job_id": job_ids[0], "technician_id": tech_id})
    print(f"Assign Job 1 Result: {resp.status_code}, {resp.text}")
    assert resp.status_code == 200
    assert "Technician assigned successfully" in resp.json()["message"]
    
    # Check workload
    resp = client.get(f"/technicians/workload?technician_id={tech_id}")
    print(f"Workload 1 Result: {resp.status_code}, {resp.json()}")
    assert resp.status_code == 200
    assert resp.json()["current_jobs"] == 1
    assert resp.json()["can_assign"] == True

    # 4. Assign 2nd Job
    resp = client.post("/assign-job", json={"job_id": job_ids[1], "technician_id": tech_id})
    print(f"Assign Job 2 Result: {resp.status_code}, {resp.text}")
    assert resp.status_code == 200
    
    # Check workload
    resp = client.get(f"/technicians/workload?technician_id={tech_id}")
    print(f"Workload 2 Result: {resp.status_code}, {resp.json()}")
    assert resp.status_code == 200
    assert resp.json()["current_jobs"] == 2
    assert resp.json()["can_assign"] == False
    
    # Check technician status
    db.refresh(tech)
    assert tech.technician_status == "BUSY"

    # 5. Assign 3rd Job (Should Fail)
    resp = client.post("/assign-job", json={"job_id": job_ids[2], "technician_id": tech_id})
    print(f"Assign Job 3 Result: {resp.status_code}, {resp.text}")
    assert resp.status_code == 400
    assert "Workload limit reached" in resp.json()["error"]

    print("Verification successful!")

if __name__ == "__main__":
    test_workload_limitation()
