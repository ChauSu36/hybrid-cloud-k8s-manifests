import os, time, argparse
from collector import init_k8s, collect_pod_context, query_prometheus_cpu
from analyzer import analyze_cluster_context

def run_once(v1, namespace, label, prom_url):
    pods_data = collect_pod_context(v1, namespace, label)
    cpu_data = query_prometheus_cpu(prom_url, namespace)
    report = analyze_cluster_context(pods_data, cpu_data)
    print(report.model_dump_json(indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Chạy 1 lần dạng CLI rồi thoát")
    args = parser.parse_args()

    v1 = init_k8s()
    ns = os.getenv("TARGET_NAMESPACE", "jobportal")
    label = os.getenv("TARGET_LABEL", "app=jobportal-backend")
    prom_url = os.getenv("PROMETHEUS_URL", "https://metrics.chausu.name.vn")

    if args.once:
        run_once(v1, ns, label, prom_url)
    else:
        while True:
            run_once(v1, ns, label, prom_url)
            time.sleep(30)
