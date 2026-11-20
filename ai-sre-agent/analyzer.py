import os
import re
import json
import itertools
from google import genai
from schemas import IncidentReport

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
]
_model_cycle = itertools.cycle(MODELS)

def _extract_json(text: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    return cleaned.strip()

def analyze_cluster_context(pod_context: list, cpu_metrics) -> IncidentReport:
    schema_json = json.dumps(IncidentReport.model_json_schema(), ensure_ascii=False)
    prompt = f"""
    Bạn là chuyên gia Kubernetes SRE. Hãy phân tích dữ liệu telemetry từ cụm OpenStack (namespace jobportal):
    - Ưu tiên cao nhất cho lỗi trong Application Logs (như JDBC/MySQL timeout, 500 error, OOMKilled).
    - Kết hợp CPU metrics từ Prometheus (ngưỡng cảnh báo là > 0.4 core) để phát hiện CPU bottleneck hoặc traffic burst.
    - Nếu mọi thứ bình thường và không có lỗi nghiêm trọng, đặt status là HEALTHY.
    - Trả về DUY NHẤT một chuỗi JSON hợp lệ tuân thủ đúng JSON Schema sau (không giải thích thêm):
    {schema_json}

    [PROMETHEUS CPU METRICS]
    {json.dumps(cpu_metrics, indent=2)}

    [POD LOGS & K8S EVENTS]
    {json.dumps(pod_context, indent=2)}
    """

    last_err = None
    # Round-robin chọn điểm bắt đầu, kết hợp failover thử lần lượt hết danh sách nếu lỗi
    start_model = next(_model_cycle)
    start_idx = MODELS.index(start_model)
    ordered_models = MODELS[start_idx:] + MODELS[:start_idx]

    for model_name in ordered_models:
        try:
            print(f"[INFO] Đang phân tích bằng model: {model_name}...")
            if model_name.startswith("gemini"):
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": IncidentReport,
                        "temperature": 0.1,
                    },
                )
                return IncidentReport.model_validate_json(response.text)
            else:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"temperature": 0.1},
                )
                return IncidentReport.model_validate_json(_extract_json(response.text))
        except Exception as e:
            print(f"[WARN] Model {model_name} gặp lỗi ({e}), đang chuyển sang model dự phòng...")
            last_err = e
            continue

    raise RuntimeError(f"Tất cả model đều thất bại. Lỗi cuối cùng: {last_err}")
