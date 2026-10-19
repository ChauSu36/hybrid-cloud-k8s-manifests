# Hybrid-Cloud Kubernetes Infrastructure Manifests

Hệ thống hạ tầng Kubernetes đa đám mây kết hợp giữa OpenStack On-premise và Google Cloud Platform (GKE).

## Phân chia kiến trúc:
- **clusters/google-cloud/**: Cụm Central Observability Hub tiếp nhận Metrics (Prometheus Remote Write) và Logs qua Cloud Ingress có áp dụng thuật toán Token/Leaky Bucket Rate Control.
- **clusters/openstack-onpremise/**: Cụm Workload On-premise chạy Web Fullstack (JobPortal: React, Spring Boot, MySQL), Prometheus Agent và Fluent Bit.
