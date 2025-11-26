from locust import HttpUser, task, between
import os

class AgentReportUser(HttpUser):
    wait_time = between(0.5, 2)
    host = os.getenv("LOCUST_HOST_URL", "http://localhost:8003")

    @task(5)
    def report_hardware(self):
        payload = {
            "hardware_id": "HW" + str(self.environment.runner.user_count),
            "name": "Perf Agent",
            "dmr_config": {"revision": 1},
        }
        with self.client.post("/api/v1/host/agent/report", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"status={response.status_code}")

    @task(1)
    def report_status(self):
        payload = {
            "hardware_id": "HW" + str(self.environment.runner.user_count),
            "status": "online",
            "timestamp": "2025-01-15T10:00:00Z",
        }
        self.client.post("/api/v1/host/agent/status", json=payload)
