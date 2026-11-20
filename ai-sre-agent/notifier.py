import os
import json
import smtplib
import requests
from email.mime.text import MIMEText
from schemas import IncidentReport

def send_notification(alert_name: str, report: IncidentReport, triage_seconds: float):
    subject = f"[AI-SRE {report.status}] Alert: {alert_name} (Triage: {triage_seconds:.2f}s)"
    body = (
        f"=== BÁO CÁO PHÂN TÍCH SỰ CỐ TỰ ĐỘNG (AI-SRE) ===\n"
        f"- Alert: {alert_name}\n"
        f"- Mức độ: {report.status}\n"
        f"- Thời gian phân tích (Time-to-Triage): {triage_seconds:.2f}s\n\n"
        f"[TÓM TẮT]\n{report.summary}\n\n"
        f"[NGUYÊN NHÂN GỐC (ROOT CAUSE)]\n{report.root_cause}\n\n"
        f"[LỆNH XỬ LÝ GỢI Ý]\n" + "\n".join(f"  $ {cmd}" for cmd in report.remediation_commands)
    )

    # 1. Gửi qua Webhook (Slack / Discord / Telegram bridge) nếu có biến ALERT_WEBHOOK_URL
    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        try:
            requests.post(webhook_url, json={"content": f"**{subject}**\n```{body}```", "text": f"*{subject}*\n```{body}```"}, timeout=5)
            print("[INFO] Đã gửi báo cáo RCA qua Webhook.")
        except Exception as e:
            print(f"[WARN] Gửi Webhook thất bại: {e}")

    # 2. Gửi qua Email SMTP nếu có cấu hình SMTP_HOST
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    alert_to = os.getenv("ALERT_EMAIL_TO")
    if smtp_host and smtp_user and smtp_pass and alert_to:
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = alert_to
            with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587"))) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            print(f"[INFO] Đã gửi email báo cáo RCA tới {alert_to}.")
        except Exception as e:
            print(f"[WARN] Gửi Email thất bại: {e}")
