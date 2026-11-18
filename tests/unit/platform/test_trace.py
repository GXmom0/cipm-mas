from __future__ import annotations

from datetime import datetime

from apps.platform_api.core.clock import TZ_EAST8, FixedClock
from apps.platform_api.core.trace import (
    is_valid_trace_id,
    new_agent_run_id,
    new_trace_id,
    parse_traceparent,
)
from apps.platform_api.main import create_app
from sdk.settings import CipmSettings
from tests.support import open_test_client

FIXED = datetime(2026, 11, 13, 8, 0, tzinfo=TZ_EAST8)
VALID_TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"


def test_p05_generated_trace_id_format() -> None:
    trace_id = new_trace_id()
    assert len(trace_id) == 32
    assert is_valid_trace_id(trace_id)
    assert new_agent_run_id().startswith("run_platform_")


def test_p06_traceparent_reused() -> None:
    header = f"00-{VALID_TRACE}-00f067aa0ba902b7-01"
    assert parse_traceparent(header) == VALID_TRACE


def test_p07_invalid_traceparent_ignored() -> None:
    assert parse_traceparent("not-a-traceparent") is None
    assert parse_traceparent("") is None
    assert parse_traceparent(None) is None
    assert parse_traceparent("01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01") is None


def test_p08_response_headers(tmp_path, no_network) -> None:
    settings = CipmSettings(audit_dir=str(tmp_path / "audit"), data_dir=str(tmp_path / "data"))
    app = create_app(settings, FixedClock(FIXED))
    with open_test_client(app) as client:
        response = client.get(
            "/api/v1/health",
            headers={"traceparent": f"00-{VALID_TRACE}-00f067aa0ba902b7-01"},
        )
    assert response.headers["X-Trace-Id"] == VALID_TRACE
    assert response.headers["X-Agent-Run-Id"].startswith("run_platform_")
    assert response.json()["traceId"] == VALID_TRACE