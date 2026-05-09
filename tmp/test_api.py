import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_technician_api():
    # Start the server if it's not running? 
    # Usually we assume the user will run the server or I can run it in background.
    # But for now I'll just write the script.
    
    sample_technician = {
        "technician_name": "Arun",
        "technician_skill": "AC Repair",
        "technician_location": "Chennai",
        "technician_status": "Available"
    }

    print("Testing POST /technicians...")
    try:
        response = requests.post(f"{BASE_URL}/technicians", json=sample_technician)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            tech_id = response.json().get("technician_id")
            print(f"\nTesting GET /technicians/{tech_id}...")
            get_response = requests.get(f"{BASE_URL}/technicians/{tech_id}")
            print(f"Status Code: {get_response.status_code}")
            print(f"Response: {json.dumps(get_response.json(), indent=2)}")
            
            print("\nTesting GET /technicians...")
            list_response = requests.get(f"{BASE_URL}/technicians")
            print(f"Status Code: {list_response.status_code}")
            print(f"Count: {list_response.json().get('count')}")
    except Exception as e:
        print(f"Error connecting to API: {e}. Make sure the FastAPI server is running at {BASE_URL}")

if __name__ == "__main__":
    test_technician_api()
