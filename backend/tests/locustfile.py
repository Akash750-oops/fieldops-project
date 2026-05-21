from locust import HttpUser, task, between
import uuid
import random

class HeartbeatUser(HttpUser):
    wait_time = between(1, 2)
    
    def on_start(self):
        # Generate a random tech_id for the load test
        # Note: For successful 200 OK responses, these IDs must exist in the DB.
        # Otherwise, the server returns 404 Not Found (which is still a valid load test for the endpoint routing,
        # but you might want to seed the test database with these UUIDs beforehand).
        self.tech_id = str(uuid.uuid4())
        self.headers = {
            "X-Tenant-ID": "tenant-123",
            "Authorization": "Bearer sample_token"
        }

    @task
    def send_heartbeat(self):
        self.client.post(
            f"/technicians/{self.tech_id}/heartbeat",
            headers=self.headers,
            json={
                "last_lat": random.uniform(-90.0, 90.0),
                "last_lng": random.uniform(-180.0, 180.0)
            }
        )
