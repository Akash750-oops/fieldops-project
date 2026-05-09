
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_invalid_priority_error_response():
    # Test URGENT
    response = client.post("/jobs", json={
        "customer_name": "Test",
        "location": "Loc",
        "issue": "Issue",
        "priority": "URGENT"
    })
    assert response.status_code == 400
    assert response.json() == {"error": "Invalid priority value"}
    print("Success: URGENT priority rejected with correct error message")

    # Test empty priority
    response = client.post("/jobs", json={
        "customer_name": "Test",
        "location": "Loc",
        "issue": "Issue",
        "priority": ""
    })
    assert response.status_code == 400
    assert response.json() == {"error": "Invalid priority value"}
    print("Success: Empty priority rejected with correct error message")

    # Test null priority
    response = client.post("/jobs", json={
        "customer_name": "Test",
        "location": "Loc",
        "issue": "Issue",
        "priority": None
    })
    assert response.status_code == 400
    assert response.json() == {"error": "Invalid priority value"}
    print("Success: Null priority rejected with correct error message")
    
    # Test field cannot be empty (customer_name)
    response = client.post("/jobs", json={
        "customer_name": "",
        "location": "Loc",
        "issue": "Issue",
        "priority": "LOW"
    })
    assert response.status_code == 400
    print(f"Empty customer_name response: {response.json()}")
    assert "cannot be empty" in response.json().get("error", "")

if __name__ == "__main__":
    try:
        test_invalid_priority_error_response()
        print("\nAll validation tests passed!")
    except Exception as e:
        print(f"\nValidation tests failed: {e}")
        import traceback
        traceback.print_exc()
