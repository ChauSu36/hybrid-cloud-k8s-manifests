import requests
from kubernetes import client, config

IGNORE_EVENTS = {"Scheduled", "Pulling", "Pulled", "Created", "Started"}

def init_k8s():
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()
    return client.CoreV1Api()

def collect_pod_context(v1: client.CoreV1Api, namespace: str, label_selector: str):
    pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector).items
    context_list = []

    for pod in pods:
        pod_name = pod.metadata.name
        try:
            logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=50)
        except Exception as e:
            logs = f"Could not fetch logs: {e}"

        events_raw = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={pod_name}"
        ).items
        events = [
            f"[{e.type}] {e.reason}: {e.message}"
            for e in events_raw if e.reason not in IGNORE_EVENTS
        ]

        context_list.append({
            "pod": pod_name,
            "phase": pod.status.phase,
            "logs": logs,
            "events": events
        })
    return context_list

def query_prometheus_cpu(prom_url: str, namespace: str):
    promql = f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", container!=""}}[1m])) by (pod)'
    try:
        resp = requests.get(f"{prom_url}/api/v1/query", params={"query": promql}, timeout=5)
        return resp.json().get("data", {}).get("result", [])
    except Exception as e:
        return f"Prometheus query failed: {e}"
