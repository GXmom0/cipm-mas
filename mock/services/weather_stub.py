from __future__ import annotations

import os
from typing import Any

from mock.seed import iso_after

WEATHER_VERSION = "WX-2026.11.13-0600"


def _provider() -> str:
    return (os.environ.get("CIPM_WEATHER_PROVIDER") or "mock").strip().lower()


def _mock_forecast(plot_no: str) -> dict[str, Any]:
    if plot_no == "PLOT-0916":
        daily = [
            {"date": "2026-11-13", "minT": 11.8, "avgT": 22.4},
            {"date": "2026-11-14", "minT": 12.1, "avgT": 22.9},
            {"date": "2026-11-15", "minT": 12.6, "avgT": 23.4},
        ]
    else:
        daily = [
            {"date": "2026-11-13", "minT": 13.6, "avgT": 24.8},
            {"date": "2026-11-14", "minT": 13.2, "avgT": 24.2},
            {"date": "2026-11-15", "minT": 13.8, "avgT": 25.1},
        ]
    hourly = [
        {
            "at": iso_after(hours=hour),
            "windLevel": 2 if hour % 5 else 3,
            "rhPct": 34 if 14 <= hour % 24 <= 18 else 46,
        }
        for hour in range(72)
    ]
    return {
        "plotNo": plot_no,
        "version": WEATHER_VERSION,
        "publishedAt": iso_after(minutes=-120),
        "hourly": hourly,
        "daily": daily,
    }


def get_forecast(plot_no: str, *, logger: Any = None) -> dict[str, Any]:
    if _provider() == "openmeteo":
        try:
            from adapters.weather.openmeteo import fetch_forecast

            return fetch_forecast(plot_no, logger=logger)
        except Exception:  # noqa: BLE001 - 降级回退 mock，演示不中断
            return _mock_forecast(plot_no)
    return _mock_forecast(plot_no)