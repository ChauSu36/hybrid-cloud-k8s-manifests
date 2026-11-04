# ☁️ Hybrid-Cloud Kubernetes Platform & Observability Hub

## 📖 Project Overview
This repository contains the declarative Kubernetes manifests and configuration files for a **Hybrid Multi-Cluster Kubernetes architecture** spanning across OpenStack (On-Premise) and Google Cloud Platform (GKE). 

The core objective of this project is to separate the application workloads from the heavy observability stack, ensuring high availability and zero resource contention. It features cross-cluster metric forwarding, centralized logging, and Ingress rate-limiting to protect the system against bursty traffic.

## 🏗️ System Architecture
![Hybrid-Cloud Architecture](assets/hybrid-cloud-architecture.png)

**Traffic Flow:**
1. **End-users & Load Testing:** Traffic is routed through Cloudflare Edge (WAF/CDN) via a secure Cloudflare Tunnel to the OpenStack workload cluster.
2. **Workload Cluster (OpenStack):** Hosts the Job Portal web application. Nginx Ingress filters and rate-limits traffic using the Token Bucket algorithm.
3. **Observability Hub (GKE):** Prometheus Agents on OpenStack push telemetry data (via Remote Write) to the Central Prometheus Server on GKE. Alertmanager triggers notifications if resource thresholds are breached.

## 🛠️ Tech Stack
- **Cloud Infrastructure:** Google Kubernetes Engine (GKE), OpenStack.
- **Container Orchestration:** Kubernetes, Docker, Helm, ArgoCD (GitOps).
- **Monitoring & Alerting:** Prometheus (Agent & Central), Grafana, Alertmanager.
- **Logging:** Elasticsearch, Fluent Bit, Kibana (ELK Stack).
- **Networking & Security:** Nginx Ingress Controller, Cloudflare (DNS, WAF, Tunnel).
- **Load Testing:** Locust.

## 🚀 Key Technical Implementations
- **Traffic Policing (Token Bucket Algorithm):** Configured Nginx Ingress with `ngx_http_limit_req_module` (limit-rps: 100, burst: 200) to protect the backend from bursty traffic and simulate HTTP 429 rate-limiting.
- **Cross-Cluster Telemetry (Push-based):** Shifted from traditional pull-based monitoring to a Push-based model using **Prometheus Remote Write** to bypass On-Premise NAT/Firewall restrictions.
- **Automated Incident Alerting:** Integrated Alertmanager with Grafana to trigger email notifications when Pod CPU usage exceeds the 0.4 core threshold (`K8sPodCPUHighUsage`).
- **GitOps Delivery:** Managed cloud resources and configurations declaratively using ArgoCD and Helm charts for reproducible rollouts.

## 📂 Repository Structure
```text
hybrid-cloud-k8s-manifests/
├── openstack-onpremise/
│   ├── app-jobportal/         # ReactJS, Spring Boot, MySQL manifests
│   ├── ingress/               # Nginx Ingress with Token Bucket config
│   └── telemetry-agents/      # Prometheus Agent & Fluent Bit DaemonSet
└── google-cloud/
    ├── monitoring/            # Central Prometheus, Grafana, Alertmanager
    └── logging/               # Elasticsearch & Kibana manifests