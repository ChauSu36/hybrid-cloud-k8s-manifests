Tài liệu quy trình ứng cứu sự cố chuẩn (SOP) dành cho kỹ sư trực ca (On-call SRE) khi tiếp nhận cảnh báo từ Grafana Alerting (`K8S Alerts / k8s-fast-eval`).

---

## 1. Runbook: `K8sPodCPUHighUsage` (Cảnh báo CPU Pod vượt ngưỡng)

* **Signal nhận diện:** Alert `K8sPodCPUHighUsage` chuyển trạng thái `Firing` (`severity: warning`) khi CPU thực tế của Pod trong namespace `jobportal` vượt `0.08 cores` (80m) liên tục trên 1 phút.
* **Phạm vi ảnh hưởng (Blast Radius):** Cô lập trong Pod gây tải thuộc namespace `jobportal` trên cụm OpenStack; không ảnh hưởng các namespace hệ thống (`kube-system`, `monitoring`, `logging`) hay cụm GKE.
* **Các bước điều tra (`kubectl`):**
  1. Xác định Pod chiếm dụng CPU cao nhất:
     ```bash
     kubectl top pods -n jobportal
     ```
  2. Kiểm tra cấu hình `requests/limits` và sự kiện container:
     ```bash
     kubectl describe pod <pod-name> -n jobportal
     ```
  3. Kiểm tra log tiến trình đang chạy bên trong Pod:
     ```bash
     kubectl logs <pod-name> -n jobportal --tail=50
     ```
  4. Đánh giá mức tải phần cứng trên các Node:
     ```bash
     kubectl top nodes
     ```
* **Quy trình Recovery / Rollback:**
  * *Lưu ý:* Tuyệt đối không reboot Node hay restart toàn bộ Deployment khi chưa xác định nguồn tải.
  * Nếu do Pod kiểm thử tải cô lập (`cpu-stress-test`):
    ```bash
    kubectl delete pod cpu-stress-test -n jobportal
    ```
  * Nếu do lưu lượng truy cập tăng đột biến: Dừng tool phát tải (Locust) hoặc scale-out replica qua GitOps.
  * **Xác minh:** Biểu đồ CPU hạ về mức nền (`< 0.08 cores`) và Alert trên Grafana tự động chuyển về `Normal`.

---

## 2. Runbook: `K8sDeploymentReplicaMismatch` (Thiếu hụt bản sao khả dụng)

* **Signal nhận diện:** Alert `K8sDeploymentReplicaMismatch` chuyển trạng thái `Firing` (`severity: critical`) khi `Desired Replicas - Available Replicas > 0` kéo dài trên 1 phút.
* **Phạm vi ảnh hưởng (Blast Radius):** Cô lập tại Deployment gặp sự cố trong namespace `jobportal`; các dịch vụ nghiệp vụ khác (`frontend`, `backend`, `mysql`) vẫn duy trì hoạt động bình thường.
* **Các bước điều tra (`kubectl`):**
  1. Kiểm tra trạng thái tổng thể của Deployment và các Pod:
     ```bash
     kubectl get deployments,pods -n jobportal -o wide
     ```
  2. Xem chi tiết điều kiện lỗi của Deployment:
     ```bash
     kubectl describe deployment <deployment-name> -n jobportal
     ```
  3. Xác định nguyên nhân crash (`Exit Code`, `CrashLoopBackOff`, `OOMKilled`):
     ```bash
     kubectl describe pod <pod-name> -n jobportal
     ```
  4. Đọc log của container ngay trước thời điểm bị sập:
     ```bash
     kubectl logs <pod-name> -n jobportal --previous --tail=50
     ```
* **Quy trình Recovery / Rollback:**
  * Nếu do Deployment kiểm thử lỗi (`crash-test-deployment`):
    ```bash
    kubectl delete deployment crash-test-deployment -n jobportal
    ```
  * Nếu do lỗi cấu hình/image sau đợt phát hành mới: Thực hiện `git revert` commit gây lỗi trên repo GitOps để ArgoCD tự động đồng bộ lại bản ổn định.
  * **Xác minh:** Lệnh `kubectl get deployments -n jobportal` hiển thị `READY` cân bằng (`Desired = Available`) và Alert quay về `Normal`.