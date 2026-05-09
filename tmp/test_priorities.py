
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_job_priority_levels():
    priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    for priority in priorities:
        response = client.post(
            "/jobs",
            json={
                "customer_name": f"Test {priority}",
                "location": "Chennai",
                "issue": "Server Down",
                "priority": priority
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["job"]["priority"] == priority
        print(f"Successfully created job with priority: {priority}")

def test_create_job_invalid_priority():
    response = client.post(
        "/jobs",
        json={
            "customer_name": "Invalid Test",
            "location": "Chennai",
            "issue": "Server Down",
            "priority": "URGENT"
        }
    )
    assert response.status_code == 400
    print("Successfully rejected invalid priority: URGENT")

def test_get_jobs():
    response = client.get("/jobs")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    print(f"Successfully fetched {len(data['jobs'])} jobs")

if __name__ == "__main__":
    try:
        test_create_job_priority_levels()
        test_create_job_invalid_priority()
        test_get_jobs()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTests failed: {e}")
        import traceback
        traceback.print_exc()
