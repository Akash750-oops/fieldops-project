from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import Technician, Job
import datetime

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

def test_detailed_validation():
    print("Starting detailed validation tests...")
    db = TestingSessionLocal()
    db.query(Job).delete()
    db.query(Technician).delete()
    db.commit()

    # 1. Setup: Technician with max_jobs=2
    resp = client.post("/technicians/", json={
        "technician_name": "Valid Tech",
        "technician_skill": "Electrician",
        "technician_location": "30,30",
        "technician_status": "AVAILABLE"
    })
    tech_id = resp.json()["technician_id"]
    
    tech = db.query(Technician).filter(Technician.technician_id == tech_id).first()
    tech.max_jobs = 2
    db.commit()

    # 2. Test: GET /validate-workload (Initial)
    resp = client.get(f"/technicians/validate-workload?technician_id={tech_id}")
    print(f"Initial Validation: {resp.json()}")
    assert resp.json()["can_assign"] == True
    assert resp.json()["message"] == "Assignment allowed"

    # 3. Test: OFFLINE status
    tech.technician_status = "OFFLINE"
    db.commit()
    resp = client.get(f"/technicians/validate-workload?technician_id={tech_id}")
    print(f"Offline Validation: {resp.json()}")
    assert resp.json()["can_assign"] == False
    assert resp.json()["message"] == "Technician is offline"

    # 4. Test: BUSY status (Max Load reached)
    tech.technician_status = "BUSY"
    tech.current_jobs = 2
    db.commit()
    resp = client.get(f"/technicians/validate-workload?technician_id={tech_id}")
    print(f"Max Load Validation: {resp.json()}")
    assert resp.json()["can_assign"] == False
    assert resp.json()["message"] == "Maximum workload reached"
    
    # 5. Test: BUSY status (Manual/Other reason)
    tech.current_jobs = 0
    db.commit()
    resp = client.get(f"/technicians/validate-workload?technician_id={tech_id}")
    print(f"Busy (Unavailable) Validation: {resp.json()}")
    assert resp.json()["can_assign"] == False
    assert resp.json()["message"] == "Technician is currently unavailable"

    # 6. Test: POST /assign-job with Max Load
    tech.current_jobs = 2
    tech.technician_status = "BUSY"
    db.commit()
    
    job_resp = client.post("/jobs/", json={
        "customer_name": "Val Cust",
        "location": "31,31",
        "issue_description": "Sparking",
        "priority": "CRITICAL",
        "service_type": "Electrician",
        "contact_number": "0000000000",
        "preferred_service_date": str(datetime.date.today()),
        "required_skill": "Electrician"
    })
    job_id = job_resp.json()["id"]
    
    assign_resp = client.post("/assign-job", json={"job_id": job_id, "technician_id": tech_id})
    print(f"Assignment Rejection Result: {assign_resp.status_code}, {assign_resp.text}")
    assert assign_resp.status_code == 400
    assert "Maximum workload reached" in assign_resp.json()["error"]

    print("All validation condition tests passed!")

if __name__ == "__main__":
    test_detailed_validation()
