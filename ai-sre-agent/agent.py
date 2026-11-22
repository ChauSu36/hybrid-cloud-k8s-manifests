import os
import time
import json
import threading
import requests
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from collector import init_k8s_client, collect_pod_diagnostics
from analyzer import analyze_cluster_context
from notifier import send_notification

v1 = init_k8s_client()
PROM_URL = os.getenv("PROMETHEUS_URL", "https://metrics.chausu.name.vn")
DEFAULT_NS = os.getenv("TARGET_NAMESPACE", "jobportal")
PROCESSED_ALERTS = set()  # Lưu fingerprint + startsAt để chống gọi lặp Gemini


def get_cpu_metrics(namespace: str):
    try:
        query = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", container!=""}}[2m])) by (pod)'
        res = requests.get(f"{PROM_URL}/api/v1/query", params={"query": query}, timeout=5).json()
        return res.get("data", {}).get("result", [])
    except Exception as e:
        return {"error": str(e)}


def process_single_alert(alert: dict):
    if alert.get("status") == "resolved":
        return {"status": "ignored", "reason": "Alert resolved"}

    start_time = time.time()
    labels = alert.get("labels", {})
    alert_name = labels.get("alertname", "ManualHealthCheck")
    namespace = labels.get("namespace", DEFAULT_NS)
    pod_name = labels.get("pod")

    print(f"[ALERT RECEIVED] {alert_name} | Namespace: {namespace} | Pod: {pod_name}", flush=True)

    # 1. Thu thập trạng thái Pod, Events & Logs (kèm fallback Elasticsearch + ẩn danh PII)
    diagnostics = collect_pod_diagnostics(v1, namespace=namespace, pod_name=pod_name)
    cpu_metrics = get_cpu_metrics(namespace=namespace)

    # 2. Gửi ngữ cảnh đã làm sạch sang Gemini phân tích Root Cause
    report = analyze_cluster_context(
        alert_name=alert_name,
        namespace=namespace,
        diagnostics=diagnostics,
        metrics=cpu_metrics,
    )
    triage_seconds = round(time.time() - start_time, 2)

    output = {
        "alert_name": alert_name,
        "namespace": namespace,
        "triage_time_seconds": triage_seconds,
        "report": report.model_dump() if hasattr(report, "model_dump") else report,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False), flush=True)

    # 3. Gửi báo cáo hướng dẫn khắc phục về Gmail
    status_val = getattr(report, "status", "CRITICAL")
    if status_val != "HEALTHY":
        send_notification(alert_name=alert_name, report=report, triage_seconds=triage_seconds)

    return output


def poll_grafana_alerts():
    grafana_url = os.getenv("GRAFANA_URL", "https://grafana.chausu.name.vn").rstrip("/")
    grafana_token = os.getenv("GRAFANA_API_TOKEN", "")
    interval = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
    endpoint = f"{grafana_url}/api/alertmanager/grafana/api/v2/alerts"
    headers = {"Authorization": f"Bearer {grafana_token}"}

    print(f"[POLLER] Started Outbound Polling every {interval}s -> {endpoint}", flush=True)
    while True:
        try:
            if grafana_token:
                resp = requests.get(endpoint, headers=headers, timeout=8)
                resp.raise_for_status()
                for alert in resp.json():
                    state = alert.get("status", {}).get("state", "")
                    dedup_key = f"{alert.get('fingerprint', '')}_{alert.get('startsAt', '')}"

                    if state == "active" and dedup_key not in PROCESSED_ALERTS:
                        PROCESSED_ALERTS.add(dedup_key)
                        process_single_alert({
                            "status": "firing",
                            "labels": alert.get("labels", {}),
                            "annotations": alert.get("annotations", {}),
                        })
        except Exception as e:
            print(f"[POLLER-WARN] Grafana API polling error: {e}", flush=True)

        time.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    poller_thread = threading.Thread(target=poll_grafana_alerts, daemon=True)
    poller_thread.start()
    yield


app = FastAPI(title="AI-SRE Alert Triage Agent v4", lifespan=lifespan)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": "v4"}


@app.post("/webhook")
async def alertmanager_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    alerts = payload.get("alerts") or [{"labels": {"alertname": "ManualHealthCheck", "namespace": DEFAULT_NS}}]
    results = [process_single_alert(a) for a in alerts]
    return {"results": results}
