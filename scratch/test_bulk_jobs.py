import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'backend')))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_bulk_create_jobs():
    data = [
      {
        "customer_name": "Test User 1",
        "location": "Chennai",
        "issue_description": "AC issue",
        "priority": "Critical",
        "service_type": "HVAC Repair",
        "contact_number": "9876543210",
        "preferred_service_date": "2026-05-14",
        "required_skill": "AC Repair",
        "status": "Active"
      },
      {
        "customer_name": "Test User 2",
        "location": "Coimbatore",
        "issue_description": "Power issue",
        "priority": "High",
        "service_type": "Electrical Service",
        "contact_number": "9876543211",
        "preferred_service_date": "2026-05-15",
        "required_skill": "Electrical",
        "status": "In Progress"
      }
    ]
    
    response = client.post("/jobs/", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_bulk_create_jobs()
