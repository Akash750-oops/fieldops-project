import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'backend')))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_bulk_create():
    data = [
      {
        "technician_name": "Bulk Tech 1",
        "technician_skill": "AC Repair",
        "technician_location": "Chennai",
        "technician_status": "AVAILABLE"
      },
      {
        "technician_name": "Bulk Tech 2",
        "technician_skill": "Electrical",
        "technician_location": "Coimbatore",
        "technician_status": "AVAILABLE"
      }
    ]
    
    response = client.post("/technicians/", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_bulk_create()
