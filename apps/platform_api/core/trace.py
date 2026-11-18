from __future__ import annotations

import re
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

TRACE_HEADER = "traceparent"
TRACE_RESPONSE_HEADER = "X-Trace-Id"
AGENT_RUN_RESPONSE_HEADER = "X-Agent-Run-Id"
_TRACE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_TRACEPARENT_PATTERN = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def new_trace_id() -> str:
    return secrets.token_hex(16)


def parse_traceparent(value: str | None) -> str | None:
    if not value:
        return None
    matched = _TRACEPARENT_PATTERN.match(value.strip())
    if not matched:
        return None
    return matched.group(1)


def is_valid_trace_id(value: str) -> bool:
    return bool(_TRACE_ID_PATTERN.match(value))


def new_agent_run_id(prefix: str = "run_platform") -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        trace_id = parse_traceparent(request.headers.get(TRACE_HEADER)) or new_trace_id()
        agent_run_id = new_agent_run_id()
        request.state.trace_id = trace_id
        request.state.agent_run_id = agent_run_id
        response = await call_next(request)
        response.headers[TRACE_RESPONSE_HEADER] = trace_id
        response.headers[AGENT_RUN_RESPONSE_HEADER] = agent_run_id
        return response


def trace_id_of(request: Request) -> str:
    return getattr(request.state, "trace_id", "") or new_trace_id()


def agent_run_id_of(request: Request) -> str:
    return getattr(request.state, "agent_run_id", "") or new_agent_run_id()