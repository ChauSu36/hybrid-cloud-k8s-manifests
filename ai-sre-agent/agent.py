import os
import time
import json
import requests
from fastapi import FastAPI, Request
from collector import init_k8s_client, collect_pod_diagnostics
from analyzer import analyze_cluster_context
from notifier import send_notification

app = FastAPI(title="AI-SRE Alert Triage Agent v2")
v1 = init_k8s_client()
PROM_URL = os.getenv("PROMETHEUS_URL", "https://metrics.chausu.name.vn")
DEFAULT_NS = os.getenv("TARGET_NAMESPACE", "jobportal")

def get_cpu_metrics(namespace: str):
    try:
        query = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", container!=""}}[2m])) by (pod)'
        res = requests.get(f"{PROM_URL}/api/v1/query", params={"query": query}, timeout=5).json()
        return res.get("data", {}).get("result", [])
    except Exception as e:
        return {"error": str(e)}

@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": "v2"}

@app.post("/webhook")
async def alertmanager_webhook(request: Request):
    start_time = time.time()
    payload = await request.json()
    alerts = payload.get("alerts", [])

    # Nếu gọi test thủ công với payload trống, quét toàn bộ namespace mặc định
    if not alerts:
        alerts = [{"labels": {"alertname": "ManualHealthCheck", "namespace": DEFAULT_NS}}]

    results = []
    for alert in alerts:
        if alert.get("status") == "resolved":
            continue

        labels = alert.get("labels", {})
        alert_name = labels.get("alertname", "UnknownAlert")
        namespace = labels.get("namespace", DEFAULT_NS)
        pod_name = labels.get("pod")

        print(f"\n[ALERT RECEIVED] {alert_name} | namespace={namespace} | pod={pod_name}")
        pods_data = collect_pod_diagnostics(v1, namespace=namespace, pod_name=pod_name)
        cpu_data = get_cpu_metrics(namespace)

        report = analyze_cluster_context(pods_data, cpu_data)
        triage_duration = round(time.time() - start_time, 2)

        output = {
            "alert": alert_name,
            "triage_time_seconds": triage_duration,
            "report": report.model_dump()
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

        send_notification(alert_name, report, triage_duration)
        results.append(output)

    return {"processed": len(results), "results": results}
