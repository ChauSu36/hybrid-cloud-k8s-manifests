# Incident Runbook: `K8sDeploymentReplicaMismatch` (Thiếu hụt bản sao khả dụng)

## 1. Tín hiệu cảnh báo (Signal)
- **Alert Rule:** `K8sDeploymentReplicaMismatch` (Folder: `K8S Alerts`, Group: `k8s-fast-eval`)
- **Severity:** `critical`
- **PromQL Query:** `kube_deployment_spec_replicas{cluster="openstack-onpremise", namespace="jobportal"} - kube_deployment_status_replicas_available{cluster="openstack-onpremise", namespace="jobportal"}`
- **Điều kiện kích hoạt:** Hiệu số `Desired Replicas - Available Replicas > 0` trong namespace `jobportal` duy trì liên tục trên `1m` (`Pending period: 1m`).

## 2. Phạm vi ảnh hưởng (Blast Radius)
- **Phạm vi cô lập:** Giới hạn tại Deployment gặp sự cố trong namespace `jobportal` trên cụm OpenStack On-premise.
- **Đảm bảo an toàn:** Các dịch vụ nghiệp vụ khác (`jobportal-frontend-deployment`, `jobportal-backend-deployment`, `mysql-0`), các namespace hệ thống (`kube-system`, `monitoring`, `logging`, `ingress-nginx`, `argocd`) và cụm GKE (Central Observability Hub) vẫn duy trì hoạt động bình thường.

## 3. Các bước điều tra (`kubectl` Verification)
1. **Kiểm tra trạng thái tổng thể của Deployment và các Pod (`kubectl get`):**
   ```bash
   kubectl get deployments,pods -n jobportal -o wide
   ```
   *Mục đích:* Xác định Deployment đang thiếu bản sao (`READY` / `AVAILABLE` nhỏ hơn `DESIRED`) và trạng thái cụ thể của Pod lỗi (`CrashLoopBackOff`, `ImagePullBackOff`, `Pending` hoặc `OOMKilled`).

2. **Kiểm tra điều kiện triển khai và sự kiện của Deployment (`kubectl describe deployment`):**
   ```bash
   kubectl describe deployment <deployment-name> -n jobportal
   ```
   *Mục đích:* Đọc mục `Conditions` và `Events` (ví dụ `ReplicaFailure` hoặc `ProgressDeadlineExceeded`).

3. **Xác định nguyên nhân container dừng (`kubectl describe pod`):**
   ```bash
   kubectl describe pod <pod-name> -n jobportal
   ```
   *Mục đích:* Kiểm tra trường `Last State`, `Reason` và `Exit Code` (ví dụ `Exit Code: 1` do lỗi ứng dụng/command hoặc `Exit Code: 137` do tràn bộ nhớ `OOMKilled`).

4. **Đọc log của container trước thời điểm bị sập và sự kiện namespace (`kubectl logs` & `events`):**
   ```bash
   kubectl logs <pod-name> -