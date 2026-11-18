from __future__ import annotations

from datetime import datetime

import pytest

from apps.platform_api.core.clock import TZ_EAST8, FixedClock
from apps.platform_api.main import create_app
from sdk.settings import CipmSettings
from tests.support import open_test_client

FIXED = datetime(2026, 11, 13, 8, 0, tzinfo=TZ_EAST8)


@pytest.fixture
def client(tmp_path, no_network):
    settings = CipmSettings(
        audit_dir=str(tmp_path / "audit"),
        data_dir=str(tmp_path / "data"),
    )
    app = create_app(settings, FixedClock(FIXED))
    with open_test_client(app) as test_client:
        yield test_client


def test_p13_health_fields(client) -> None:
    payload = client.get("/api/v1/health").json()
    data = payload["data"]
    assert data["status"] == "ok"
    assert data["mock"] is True
    assert data["runtime"] == "local"
    assert data["version"] == "0.1.0"
    assert "dependencies" in data
    assert data["serverTime"].endswith("+08:00")


def test_p14_dashboard_plots_and_badges(client) -> None:
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["plots"]) == 5
    badges = {badge for plot in data["plots"] for badge in plot["badges"]}
    assert badges == {"BLOCKED", "DEGRADED", "REFUSED", "RESCHEDULED"}
    assert response.headers["X-Snapshot-At"].endswith("+08:00")


def test_p15_farm_filter(client) -> None:
    data = client.get("/api/v1/dashboard", params={"farmNo": "FARM-XJ-HT-01"}).json()["data"]
    assert len(data["plots"]) == 5
    empty = client.get("/api/v1/dashboard", params={"farmNo": "FARM-UNKNOWN"}).json()["data"]
    assert empty["plots"] == []


def test_p16_stage_passthrough(client) -> None:
    data = client.get("/api/v1/dashboard", params={"stage": "patrol"}).json()["data"]
    assert data["stage"] == "patrol"