import sys
import os
import importlib.util

env_path = os.path.abspath(os.path.join(os.getcwd(), "..", "env", "Lib", "site-packages"))
if env_path not in sys.path:
    sys.path.insert(0, env_path)
sys.path.insert(0, os.getcwd())

spec = importlib.util.spec_from_file_location("py", os.path.join(env_path, "py", "__init__.py"))
real_py = importlib.util.module_from_spec(spec)
sys.modules["py"] = real_py
spec.loader.exec_module(real_py)

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test():
    print("Running test_assign_correct_technician manual check...")
    response = client.post("/assign-job", json={
        "job_id": "JOB1",
        "job_type": "AC Repair"
    })
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")

if __name__ == "__main__":
    test()
