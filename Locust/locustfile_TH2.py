from locust import HttpUser, task, between
import uuid

class JobPortalPhase3Test(HttpUser):
    # Giãn cách ngắn để tạo áp lực liên tục lên Ingress
    wait_time = between(0.1, 0.3)

    @task(1)
    def test_backend_rate_limit(self):
        """Bơm tải vào API Login để ghi nhận việc Ingress chặn bằng mã HTTP 429"""
        payload = {"email": "test@gmail.com", "password": "wrongpassword123"}
        headers = {
            "Content-Type": "application/json",
            "X-Request-ID": f"LOCUST-{uuid.uuid4().hex[:8]}"
        }

        # BẮT BUỘC CẦN catch_response=True VÀ name
        with self.client.post(
            "https://api.chausu.name.vn/auth/login",
            json=payload,
            headers=headers,
            name="[Dynamic] POST /auth/login",
            catch_response=True
        ) as response:
            if response.status_code == 429:
                # Ghi nhận HTTP 429 vào tab Failures để lấy minh chứng Token Bucket hoạt động
                response.failure("HTTP 429: Rate Limited by Token Bucket")
            elif response.status_code == 401:
                # 401 do sai mật khẩu -> Pod Backend xử lý bình thường -> tính là thành công
                response.success()
            elif response.status_code >= 500:
                response.failure(f"Server error: {response.status_code}")
            else:
                response.success()
            
        