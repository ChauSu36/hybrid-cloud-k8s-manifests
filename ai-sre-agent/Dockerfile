# --- Stage 1: Builder (Cài đặt thư viện vào virtual environment) ---
FROM python:3.10-slim AS builder

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Runtime (Image siêu nhẹ, không chứa pip/build tools) ---
FROM python:3.10-slim

WORKDIR /app

# Chỉ copy môi trường ảo đã cài sẵn thư viện từ stage builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY schemas.py sanitizer.py collector.py analyzer.py notifier.py agent.py .

# Chạy dưới quyền user non-root (uid 1000) để tuân thủ SecurityContext
RUN useradd -m -u 1000 sreuser
USER 1000


EXPOSE 8000
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8000"]
