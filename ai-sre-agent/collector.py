import os
import requests
from kubernetes import client, config
from sanitizer import redact_sensitive_data

def init_k8s_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api()

def _extract_container_statuses(pod) -> list:
    statuses = []
    for cs in (pod.status.container_statuses or []):
        info = {"name": cs.name, "ready": cs.ready, "restart_count": cs.restart_count}
        if cs.state.waiting:
            info["state"] = f"Waiting ({cs.state.waiting.reason}: {cs.state.waiting.message})"
        elif cs.state.terminated:
            info["state"] = f"Terminated ({cs.state.terminated.reason}, exit_code={cs.state.terminated.exit_code})"
        elif cs.state.running:
            info["state"] = "Running"

        if cs.last_state and cs.last_state.terminated:
            info["last_terminated"] = f"{cs.last_state.terminated.reason} (exit_code={cs.last_state.terminated.exit_code})"
        statuses.append(info)
    return statuses
def fetch_elasticsearch_logs(namespace: str, pod_name: str, limit: int = 15) -> str:
    es_url = os.getenv("ELASTICSEARCH_URL", "https://logs.chausu.name.vn").rstrip("/")
    es_api_key = os.getenv("ELASTICSEARCH_API_KEY", "")
    if not es_api_key:
        return "Chưa cấu hình ELASTICSEARCH_API_KEY."

    headers = {
        "Authorization": f"ApiKey {es_api_key}",
        "Content-Type": "application/json",
    }
    query = {
        "size": limit,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {
            "bool": {
                "must": [
                    {"match": {"kubernetes.namespace_name": namespace}},
                    {"match": {"kubernetes.pod_name": pod_name}},
                ]
            }
        },
    }
    try:
        resp = requests.post(
            f"{es_url}/k8s-logs-*/_search",
            headers=headers,
            json=query,
            timeout=8,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        if not hits:
            return "Không tìm thấy log lịch sử trên Elasticsearch."
        lines = [h.get("_source", {}).get("log", "").strip() for h in reversed(hits)]
        return redact_sensitive_data("\n".join(lines)[-2500:])
    except Exception as e:
        return f"Lỗi truy vấn Elasticsearch: {str(e)}"
def collect_pod_diagnostics(v1: client.CoreV1Api, namespace: str, pod_name: str = None, label_selector: str = None) -> list:
    if pod_name:
        try:
            pods = [v1.read_namespaced_pod(name=pod_name, namespace=namespace)]
        except Exception:
            pods = v1.list_namespaced_pod(namespace=namespace).items
    elif label_selector:
        pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector).items
    else:
        pods = v1.list_namespaced_pod(namespace=namespace).items

    events = v1.list_namespaced_event(namespace=namespace).items
    diagnostics = []

    for pod in pods:
        name = pod.metadata.name
        if name.startswith("ai-sre-agent"):
            continue

        pod_events = [
            f"[{e.type}] {e.reason}: {redact_sensitive_data(e.message)}"
            for e in events
            if e.involved_object.name == name and e.type == "Warning"
        ][-10:]

        try:
            raw_logs = v1.read_namespaced_pod_log(name=name, namespace=namespace, tail_lines=20)
            if raw_logs and raw_logs.strip():
                clean_logs = redact_sensitive_data(raw_logs[-2500:])
            else:
                clean_logs = f"[Fallback Elasticsearch Logs]\n{fetch_elasticsearch_logs(namespace, name)}"
        except Exception as e:
            es_fallback = fetch_elasticsearch_logs(namespace, name)
            clean_logs = f"K8s API Log lỗi ({str(e)}). [Fallback Elasticsearch Logs]:\n{es_fallback}"

        diagnostics.append({
            "pod_name": name,
            "phase": pod.status.phase,
            "node": pod.spec.node_name,
            "container_statuses": _extract_container_statuses(pod),
            "warning_events": pod_events,
            "recent_logs": clean_logs,
        })

    return diagnostics
