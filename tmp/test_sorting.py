import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def setup_sample_jobs():
    jobs_to_create = [
        {"customer_name": "Low User", "location": "Loc A", "issue": "Problem A", "priority": "LOW"},
        {"customer_name": "High User", "location": "Loc B", "issue": "Problem B", "priority": "HIGH"},
        {"customer_name": "Medium User", "location": "Loc C", "issue": "Problem C", "priority": "MEDIUM"},
        {"customer_name": "Critical User", "location": "Loc D", "issue": "Problem D", "priority": "CRITICAL"},
        {"customer_name": "Another High User", "location": "Loc E", "issue": "Problem E", "priority": "HIGH"},
    ]
    
    print("Creating sample jobs...")
    for job in jobs_to_create:
        requests.post(f"{BASE_URL}/jobs", json=job)

def test_job_sorting():
    print("Testing GET /jobs/sorted...")
    try:
        response = requests.get(f"{BASE_URL}/jobs/sorted")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])
            print(f"Total jobs: {len(jobs)}")
            
            priorities = [job["priority"] for job in jobs]
            print(f"Priority sequence: {priorities}")
            
            # Expected order of levels logic: CRITICAL before HIGH, HIGH before MEDIUM, MEDIUM before LOW
            level_map = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}
            
            is_sorted = True
            for i in range(len(priorities) - 1):
                if level_map[priorities[i]] > level_map[priorities[i+1]]:
                    is_sorted = False
                    break
            
            if is_sorted:
                print("✅ SUCCESS: Jobs are sorted correctly by priority!")
            else:
                print("❌ FAILURE: Jobs are NOT sorted correctly by priority.")
                
            # Print the first few for visual check
            for i, job in enumerate(jobs[:5]):
                print(f"{i+1}. {job['customer_name']} - Priority: {job['priority']}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error connecting to API: {e}. Make sure the FastAPI server is running at {BASE_URL}")

if __name__ == "__main__":
    setup_sample_jobs()
    test_job_sorting()
