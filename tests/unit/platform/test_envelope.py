from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from apps.platform_api.core.clock import TZ_EAST8, FixedClock
from apps.platform_api.core.errors import BizError
from apps.platform_api.main import create_app
from sdk.contracts.error_codes import ErrorCode
from sdk.settings import CipmSettings
from tests.support import open_test_client

FIXED = datetime(2026, 11, 13, 8, 0, tzinfo=TZ_EAST8)
ENVELOPE_FIELDS = {
    "code",
    "message",
    "traceId",
    "agentRunId",
    "bizId",
    "data",
    "timestamp",
    "retryable",
}


def make_app(tmp_path):
    settings = CipmSettings(
        audit_dir=str(tmp_path / "audit"),
        data_dir=str(tmp_path / "data"),
    )
    return create_app(settings, FixedClock(FIXED))


@contextmanager
def make_client(tmp_path):
    with open_test_client(make_app(tmp_path)) as client:
        yield client


# 路由面随 execution 下发入口新增而扩展
def test_p00_app_constructible_and_expected_routes(tmp_path) -> None:
    app = make_app(tmp_path)
    paths = set(app.openapi()["paths"])
    assert paths == {
        "/api/v1/health",
        "/api/v1/dashboard",
        "/api/v1/agents/decision/invoke",
        "/api/v1/agents/execution/dispatch",
        "/api/v1/agents/execution/cancel",
    }


def test_p01_success_envelope(tmp_path, no_network) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == ENVELOPE_FIELDS
    assert payload["code"] == "OK"
    assert payload["retryable"] is False
    assert payload["timestamp"].endswith("+08:00")
    assert len(payload["traceId"]) == 32


def test_p02_not_found_envelope(tmp_path, no_network) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/v1/unknown")
    assert response.status_code == 404
    payload = response.json()
    assert set(payload) == ENVELOPE_FIELDS
    assert payload["code"] != "OK"
    assert "接口不存在" in payload["message"]


def test_p03_biz_error_mapping(tmp_path, no_network) -> None:
    app = make_app(tmp_path)

    def boom() -> None:
        raise BizError(ErrorCode.PATROL_BLOCKED, message="该巡田任务处于阻断待复核状态，暂不生成处方。")

    app.add_api_route("/api/v1/_biz", boom, methods=["GET"])
    with open_test_client(app) as client:
        response = client.get("/api/v1/_biz")
    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "CIPM-PATROL-2001"
    assert payload["retryable"] is False
    assert "阻断" in payload["message"]


def test_p04_unhandled_exception_no_stacktrace(tmp_path, no_network) -> None:
    app = make_app(tmp_path)

    def crash() -> None:
        raise RuntimeError("内部实现细节不应外泄")

    app.add_api_route("/api/v1/_crash", crash, methods=["GET"])
    with open_test_client(app) as client:
        response = client.get("/api/v1/_crash")
    assert response.status_code == 500
    text = response.text
    assert response.json()["code"] == "CIPM-SYSTEM-9001"
    assert "traceback" not in text.lower()
    assert "内部实现细节不应外泄" not in text


def test_p04b_validation_error_envelope(tmp_path, no_network) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/v1/dashboard", params={"stage": "bad-stage"})
    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "CIPM-CONTRACT-8001"
    assert "stage" in payload["message"]