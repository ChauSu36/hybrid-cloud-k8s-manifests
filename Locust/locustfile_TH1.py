from locust import HttpUser, task, between
import uuid

class JobPortalNetworkTest(HttpUser):
    # Gian cach ngau nhien 0.1s - 0.3s de tao ap luc lien tuc len kenh truyen
    wait_time = between(0.1, 0.3)

    # @task(3)
    # def load_frontend(self):
    #     """Luong 1: Tai tai nguyen tinh UI de do kiem Cloudflare CDN Cache"""
    #     self.client.get("/", name="[Static] Web Frontend UI")

    @task(1)
    def load_backend_api(self):
        """Luong 2: Ban tai API Login de ep CPU va DB Connection Pool"""
        payload = {"email": "test@gmail.com", "password": "wrongpassword123"}
        with self.client.post("https://api.chausu.name.vn/auth/login", json=payload, name="[Dynamic] POST /auth/login", catch_response=True) as response:
            if response.status_code == 429:
                response.success()