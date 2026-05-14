from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import Technician, Job
import datetime

# Use the same setup as before
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

def test_workload_management():
    print("Starting workload management test...")
    db = TestingSessionLocal()
    db.query(Job).delete()
    db.query(Technician).delete()
    db.commit()

    # 1. Create a technician with max_jobs=1 (to test status flip)
    resp = client.post("/technicians/", json={
        "technician_name": "Sync Tech",
        "technician_skill": "HVAC",
        "technician_location": "20,20",
        "technician_status": "AVAILABLE"
    })
    tech_id = resp.json()["technician_id"]
    
    tech = db.query(Technician).filter(Technician.technician_id == tech_id).first()
    tech.max_jobs = 1
    db.commit()

    # 2. Create and Assign Job
    job_resp = client.post("/jobs/", json={
        "customer_name": "Test Cust",
        "location": "21,21",
        "issue_description": "Heat issue",
        "priority": "HIGH",
        "service_type": "HVAC",
        "contact_number": "9876543210",
        "preferred_service_date": str(datetime.date.today()),
        "required_skill": "HVAC"
    })
    job_id = job_resp.json()["id"]
    
    client.post("/assign-job", json={"job_id": job_id, "technician_id": tech_id})
    
    # Check status (should be BUSY since max_jobs=1)
    resp = client.get(f"/technicians/workload?technician_id={tech_id}")
    print(f"Workload after assignment: {resp.json()}")
    assert resp.json()["current_jobs"] == 1
    assert resp.json()["status"] == "BUSY"

    # 3. Complete Job (should reduce workload and set status to AVAILABLE)
    job_data = job_resp.json()
    job_data["status"] = "completed"
    client.put(f"/jobs/{job_id}", json=job_data)
    
    resp = client.get(f"/technicians/workload?technician_id={tech_id}")
    print(f"Workload after completion: {resp.json()}")
    assert resp.json()["current_jobs"] == 0
    assert resp.json()["status"] == "AVAILABLE"

    # 4. Manual Workload Update (PUT /update-workload)
    resp = client.put("/technicians/update-workload", json={
        "technician_id": tech_id,
        "current_jobs": 1
    })
    print(f"Workload after manual update: {resp.json()}")
    assert resp.json()["current_jobs"] == 1
    assert resp.json()["status"] == "BUSY"

    # 5. Delete Job (Create new, assign, then delete)
    job_resp = client.post("/jobs/", json={
        "customer_name": "Delete Cust",
        "location": "22,22",
        "issue_description": "Leak",
        "priority": "MEDIUM",
        "service_type": "HVAC",
        "contact_number": "1234567890",
        "preferred_service_date": str(datetime.date.today()),
        "required_skill": "HVAC"
    })
    job_id2 = job_resp.json()["id"]
    
    client.post("/assign-job", json={"job_id": job_id2, "technician_id": tech_id})
    # Count should be 2 now (1 from manual update, 1 from new assignment)
    # Status should be BUSY
    
    client.delete(f"/jobs/{job_id2}")
    
    resp = client.get(f"/technicians/workload?technician_id={tech_id}")
    print(f"Workload after job deletion: {resp.json()}")
    # Should have decremented back to 1
    assert resp.json()["current_jobs"] == 1

    print("All workload tracking tests passed!")

if __name__ == "__main__":
    test_workload_management()
