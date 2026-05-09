
from fastapi.testclient import TestClient
from app.main import app
import random

client = TestClient(app)

def test_sorting_functionality():
    # 1. Clear or ensure we have fresh data for the test if possible, 
    # but since it's a real DB, we'll just add new identifiable ones.
    test_id = random.randint(1000, 9999)
    
    jobs_to_create = [
        {"priority": "LOW", "customer_name": f"Low_{test_id}"},
        {"priority": "CRITICAL", "customer_name": f"Critical_{test_id}"},
        {"priority": "MEDIUM", "customer_name": f"Medium_{test_id}"},
        {"priority": "HIGH", "customer_name": f"High_{test_id}"},
    ]
    
    for job in jobs_to_create:
        response = client.post("/jobs", json={
            "customer_name": job["customer_name"],
            "location": "Test City",
            "issue": "Test Issue",
            "priority": job["priority"]
        })
        assert response.status_code == 200

    # 2. Fetch sorted jobs
    response = client.get("/jobs/sorted")
    assert response.status_code == 200
    data = response.json()
    jobs = data["jobs"]
    
    # Filter only our test jobs to verify order among them
    our_jobs = [j for j in jobs if str(test_id) in j["customer_name"]]
    
    priorities_received = [j["priority"] for j in our_jobs]
    expected_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    
    print(f"Priorities received: {priorities_received}")
    assert priorities_received == expected_order
    print("Verification Successful: Jobs are correctly sorted by priority!")

if __name__ == "__main__":
    try:
        test_sorting_functionality()
        print("\nAll sorting tests passed!")
    except Exception as e:
        print(f"\nSorting tests failed: {e}")
        import traceback
        traceback.print_exc()
