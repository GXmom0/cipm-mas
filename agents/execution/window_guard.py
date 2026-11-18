from __future__ import annotations

from domain.rules.work_window import WorkWindowInput, WorkWindowResult, evaluate_work_window
from mock.services.weather_stub import get_forecast


def build_window_input(weather: dict, region: str = "south") -> WorkWindowInput:
    daily = weather.get("daily") or []
    hourly = weather.get("hourly") or []
    afternoon_humidity = [
        item["rhPct"]
        for item in hourly
        if 14 <= int(str(item.get("at", ""))[11:13] or 0) <= 18
    ]
    return WorkWindowInput(
        min_temperatures=tuple(float(item["minT"]) for item in daily),
        avg_temperatures=tuple(float(item["avgT"]) for item in daily),
        wind_levels=tuple(int(item["windLevel"]) for item in hourly),
        region=region,
        afternoon_humidity_pct=min(afternoon_humidity) if afternoon_humidity else None,
        data_available=bool(daily) and bool(hourly),
    )


def evaluate_for_plot(
    plot_no: str,
    region: str = "south",
    forecast: dict | None = None,
) -> WorkWindowResult:
    weather = forecast if forecast is not None else get_forecast(plot_no)
    return evaluate_work_window(build_window_input(weather, region))