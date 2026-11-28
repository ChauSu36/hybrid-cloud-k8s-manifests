# Incident Runbook: `K8sPodCPUHighUsage` (Cảnh báo CPU Pod vượt ngưỡng)

## 1. Tín hiệu cảnh báo (Signal)
- **Alert Rule:** `K8sPodCPUHighUsage` (Folder: `K8S Alerts`, Group: `k8s-fast-eval`)
- **Severity:** `warning`
- **PromQL Query:** `sum by (pod, namespace) (rate(container_cpu_usage_seconds_total{namespace="jobportal", container!=""}[1m]))`
- **Điều kiện kích hoạt:** Mức tiêu thụ CPU thực tế của Pod trong namespace `jobportal` vượt `0.08 cores` (80m) duy trì liên tục trên `1m` (`Pending period: 1m`).
- **Lưu ý ngưỡng:** Mức `0.08 cores` là ngưỡng hạ thấp phục vụ diễn tập Fault Injection trong môi trường Lab, không phải ngưỡng Production.

## 2. Phạm vi ảnh hưởng (Blast Radius)
- **Phạm vi cô lập:** Giới hạn tại Pod gây tải trong namespace `jobportal` trên cụm OpenStack On-premise.
- **Đảm bảo an toàn:** Không ảnh hưởng tới các namespace hệ thống (`kube-system`, `monitoring`, `logging`, `ingress-nginx`, `argocd`) hoặc cụm GKE (Central Observability Hub).

## 3. Các bước điều tra (`kubectl` Verification)
1. **Kiểm tra trạng thái và phân bổ Node của các Pod (`kubectl get`):**
   ```bash
   kubectl get pods -n jobportal -o wide
   ```
   *(Nếu cụm có cài `metrics-server`, chạy thêm `kubectl top pods -n jobportal` và `kubectl top nodes`; nếu chưa cài, đối chiếu mức CPU từng Pod trực tiếp trên Grafana Dashboard).*

2. **Kiểm tra cấu hình `requests/limits`, lệnh thực thi và sự kiện của Pod nghi vấn (`kubectl describe`):**
   ```bash
   kubectl describe pod <pod-name> -n jobportal
   ```
   *Mục đích:* Xác minh tiến trình đang chạy trong container (`Command`/`Args`), kiểm tra hạn mức tài nguyên và dấu hiệu bị bóp xung nhịp (CPU Throttling).

3. **Truy xuất nhật ký tiến trình bên trong container (`kubectl logs`):**
   ```bash
   kubectl logs <pod-name> -n jobportal --tail=50
   ```
   *Mục đích:* Phân biệt giữa lưu lượng truy cập tăng đột biến (traffic spike) với tiến trình bị lặp vô hạn (infinite loop) hoặc tác vụ tính toán bất thường.

4. **Kiểm tra dòng thời gian sự kiện của namespace (`kubectl get events`):**
   ```bash
   kubectl get events -n jobportal --sort-by='.metadata.creationTimestamp' | tail -n 15
   ```

## 4. Quy trình khôi phục và hoàn tác (Rollback / Recovery)
- **Nguyên tắc an toàn:** Tuyệt đối không reboot Worker Node hoặc restart toàn bộ Deployment khi chưa xác định rõ nguyên nhân gốc (Root Cause).
- **Trường hợp 1 — Do Pod kiểm thử tải cô lập (`cpu-stress-test`):**
  ```bash
  kubectl delete pod cpu-stress-test -n jobportal
  ```
- **Trường hợp 2 — Do lưu lượng truy cập tăng đột biến (Locust / Traffic Spike):**
  - Dừng công cụ phát tải (Locust) nếu đang trong phiên kiểm thử.
  - Nếu là tải người dùng thực tế, thực hiện scale-out replica hoặc tinh chỉnh `resources` thông qua commit trên repo GitOps (`hybrid-cloud-k8s-manifests`) để ArgoCD tự động đồng bộ (`Synced / Healthy`).
- **Xác minh phục hồi (Recovery Verification):**
  1. Chạy lại `kubectl get pods -n jobportal` xác nhận Pod gây tải đã được xử lý và các dịch vụ nghiệp vụ đều `Running`.
  2. Theo dõi biểu đồ CPU trên Grafana giảm về mức nền (`< 0.08 cores`).
  3. Xác nhận trạng thái Alert Rule `K8sPodCPUHighUsage` trên Grafana Alerting tự động chuyển từ `Firing` về `Normal`.