from __future__ import annotations

from typing import Any

import pytest

from adapters.weather.beaufort import beaufort_level
from adapters.weather.coordinates import coordinates_for
from mock.services import weather_stub


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def _openmeteo_payload() -> dict[str, Any]:
    hours = [f"2026-11-13T{hour:02d}:00" for hour in range(72)]
    return {
        "hourly": {
            "time": hours,
            "temperature_2m": [20.0] * 72,
            "relative_humidity_2m": [46] * 72,
            "wind_speed_10m": [5.5] * 72,
        },
        "daily": {
            "time": ["2026-11-13", "2026-11-14", "2026-11-15"],
            "temperature_2m_min": [13.6, 13.2, 13.8],
            "temperature_2m_max": [26.0, 25.2, 26.4],
        },
    }


def test_beaufort_conversion() -> None:
    assert beaufort_level(0.2) == 0
    assert beaufort_level(0.3) == 1
    assert beaufort_level(3.4) == 3
    assert beaufort_level(5.5) == 4
    assert beaufort_level(10.8) == 6
    assert beaufort_level(32.7) == 12


def test_coordinates_per_plot_and_fallback() -> None:
    assert coordinates_for("PLOT-0912") == (41.16, 80.28)
    assert coordinates_for("PLOT-0916") == (41.20, 80.35)
    assert coordinates_for("UNKNOWN") == (41.16, 80.28)


def _real_kmh_payload() -> dict[str, Any]:
    hours = [f"2026-11-13T{hour:02d}:00" for hour in range(72)]
    return {
        "hourly_units": {"wind_speed_10m": "km/h"},
        "hourly": {
            "time": hours,
            "temperature_2m": [20.0] * 72,
            "relative_humidity_2m": [46] * 72,
            "wind_speed_10m": [19.8] * 72,
        },
        "daily": {
            "time": ["2026-11-13", "2026-11-14", "2026-11-15"],
            "temperature_2m_min": [13.6, 13.2, 13.8],
            "temperature_2m_max": [26.0, 25.2, 26.4],
        },
    }


def test_openmeteo_kmh_units_fixture(monkeypatch) -> None:
    import adapters.weather.openmeteo as openmeteo

    monkeypatch.setattr(openmeteo.httpx, "get", lambda *a, **k: _FakeResponse(_real_kmh_payload()))
    result = openmeteo.fetch_forecast("PLOT-0912")

    # 19.8 km/h ÷ 3.6 = 5.5 m/s → 蒲福 4 级（若误按 19.8 m/s 将得到 8 级）
    assert result["hourly"][0]["windLevel"] == 4


def test_openmeteo_mapping(monkeypatch) -> None:
    import adapters.weather.openmeteo as openmeteo

    monkeypatch.setattr(openmeteo.httpx, "get", lambda *a, **k: _FakeResponse(_openmeteo_payload()))
    result = openmeteo.fetch_forecast("PLOT-0912")

    assert result["plotNo"] == "PLOT-0912"
    assert len(result["hourly"]) == 72
    assert len(result["daily"]) == 3
    assert result["hourly"][0]["windLevel"] == 4
    assert result["hourly"][0]["rhPct"] == 46
    assert result["hourly"][0]["at"].endswith("+08:00")
    assert result["daily"][0]["minT"] == 13.6
    assert result["daily"][0]["avgT"] == 19.8


def test_url_has_no_api_key(monkeypatch) -> None:
    import adapters.weather.openmeteo as openmeteo

    captured: dict[str, Any] = {}

    def _get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params or {}
        return _FakeResponse(_openmeteo_payload())

    monkeypatch.setattr(openmeteo.httpx, "get", _get)
    openmeteo.fetch_forecast("PLOT-0912")
    assert "key" not in captured["url"].lower()
    assert all("key" not in str(k).lower() and "token" not in str(k).lower() for k in captured["params"])


def test_provider_mock_default(monkeypatch) -> None:
    monkeypatch.delenv("CIPM_WEATHER_PROVIDER", raising=False)
    data = weather_stub.get_forecast("PLOT-0916")
    assert data["daily"][0]["minT"] == 11.8


def test_openmeteo_failure_falls_back_to_mock(monkeypatch, caplog) -> None:
    import adapters.weather.openmeteo as openmeteo

    def _boom(*args, **kwargs):
        raise TimeoutError("boom")

    monkeypatch.setenv("CIPM_WEATHER_PROVIDER", "openmeteo")
    monkeypatch.setattr(openmeteo.httpx, "get", _boom)

    with caplog.at_level("WARNING", logger="cipm.weather"):
        data = weather_stub.get_forecast("PLOT-0916")

    assert data["daily"][0]["minT"] == 11.8
    assert any("DEGRADED" in record.message for record in caplog.records)


def test_openmeteo_failure_logs_to_injected_logger(monkeypatch) -> None:
    import adapters.weather.openmeteo as openmeteo

    class FakeLogger:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str]] = []

        def log(self, actor: str, event: str, message: str) -> None:
            self.events.append((actor, event, message))

    def _boom(*args, **kwargs):
        raise TimeoutError("boom")

    monkeypatch.setattr(openmeteo.httpx, "get", _boom)
    logger = FakeLogger()

    with pytest.raises(Exception):
        openmeteo.fetch_forecast("PLOT-0916", logger=logger)

    assert logger.events
    assert logger.events[0][1] == "DEGRADED"
    assert "PLOT-0916" in logger.events[0][2]