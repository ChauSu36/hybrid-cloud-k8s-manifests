from pydantic import BaseModel, Field
from typing import List, Literal

class LogFinding(BaseModel):
    log_snippet: str = Field(description="Dòng log lỗi hoặc bất thường quan trọng nhất")
    reason: str = Field(description="Giải thích ngắn gọn tại sao dòng log này bất thường")

class IncidentReport(BaseModel):
    status: Literal["HEALTHY", "WARNING", "CRITICAL"]
    summary: str = Field(description="Tóm tắt tình trạng pod trong 1-2 câu")
    root_cause: str = Field(description="Nguyên nhân gốc rễ (ví dụ: DB timeout, CPU throttling, Traffic burst)")
    evidence_logs: List[LogFinding] = Field(description="Các dòng log bằng chứng đã trích xuất")
    security_or_traffic_anomalies: List[str] = Field(description="Bất thường về lưu lượng/rate-limit hoặc request nghi vấn")
    remediation_commands: List[str] = Field(description="Danh sách lệnh kubectl hoặc bước khắc phục đề xuất")
