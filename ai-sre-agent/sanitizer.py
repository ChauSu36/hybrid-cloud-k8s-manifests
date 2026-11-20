import re

PATTERNS = [
    (r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer [REDACTED_TOKEN]"),
    (r"eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+", "[REDACTED_JWT]"),
    (r"(?i)(password|passwd|pwd|secret|api_key|apikey|token)[\"']?\s*[:=]\s*[\"']?[^\s\"',}]+", r"\1=[REDACTED]"),
    (r"jdbc:mysql://[^\s\"']+", "jdbc:mysql://[REDACTED_DB_URI]"),
    (r"AQ\.[A-Za-z0-9\-_]+", "[REDACTED_GOOGLE_KEY]"),
]

def redact_sensitive_data(text: str) -> str:
    if not text:
        return text
    sanitized = text
    for pattern, replacement in PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized
