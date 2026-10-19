# Google Cloud GKE - Central Observability Hub

## 1. Ingress-Nginx Controller
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace
```

## 2. Central Prometheus & Grafana (Remote Write Receiver)
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install gcp-monitoring prometheus-community/kube-prometheus-stack   --namespace monitoring   --create-namespace   --set prometheus.prometheusSpec.enableRemoteWriteReceiver=true   --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.accessModes[0]=ReadWriteOnce   --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=20Gi
```

## 3. Apply Ingress with Token/Leaky Bucket Rate Limiting
```bash
kubectl apply -f ../ingress/monitoring-ingress.yaml
```
