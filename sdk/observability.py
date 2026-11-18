from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEY_MARKS = ("authorization", "api_key", "apikey", "password", "secret", "token")
SENSITIVE_KEY_PREFIXES = ("x-obs-",)
CRED_PATTERN = re.compile(r"cred://[^\s\"']+")
SIGNATURE_PATTERN = re.compile(r"([?&](?:Signature|X-Amz-Signature)=)[^&\s\"']+", re.IGNORECASE)

LOG_FIELDS = (
    "event",
    "traceId",
    "agentRunId",
    "bizId",
    "operator",
    "result",
    "durationMs",
)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in SENSITIVE_KEY_MARKS:
        return True
    if any(mark in lowered for mark in SENSITIVE_KEY_MARKS):
        return True
    return any(lowered.startswith(prefix) for prefix in SENSITIVE_KEY_PREFIXES)


def _redact_text(text: str) -> str:
    text = CRED_PATTERN.sub("cred://***", text)
    return SIGNATURE_PATTERN.sub(r"\1***", text)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("***" if _is_sensitive_key(str(key)) else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        return _redact_text(value)
    return value


def log_record(event: str, trace_id: str, agent_run_id: str, **extra: Any) -> dict[str, Any]:
    record = {
        "event": event,
        "traceId": trace_id,
        "agentRunId": agent_run_id,
    }
    record.update(extra)
    return redact(record)