from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from adapters.weather.beaufort import beaufort_level
from adapters.weather.coordinates import coordinates_for

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_VERSION = "WX-OPENMETEO-v1"
TZ_EAST8 = timezone(timedelta(hours=8))

_logger = logging.getLogger("cipm.weather")


def _published_at() -> str:
    return datetime.now(TZ_EAST8).replace(microsecond=0).isoformat()


def _log_degraded(logger: Any, plot_no: str, reason: str) -> None:
    message = f"DEGRADED weather provider=openmeteo plot={plot_no} reason={reason}"
    if logger is not None:
        logger.log("weather", "DEGRADED", message)
    else:
        _logger.warning(message)


def _map(plot_no: str, payload: dict[str, Any]) -> dict[str, Any]:
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    temperatures = hourly.get("temperature_2m") or []
    humidities = hourly.get("relative_humidity_2m") or []
    winds = hourly.get("wind_speed_10m") or []
    wind_units = str((payload.get("hourly_units") or {}).get("wind_speed_10m", "ms")).lower()
    wind_in_kmh = "km/h" in wind_units or "kmh" in wind_units

    hourly_out: list[dict[str, Any]] = []
    for index, moment in enumerate(times[:72]):
        wind = winds[index] if index < len(winds) and winds[index] is not None else 0.0
        wind_ms = float(wind) / 3.6 if wind_in_kmh else float(wind)
        humidity = humidities[index] if index < len(humidities) and humidities[index] is not None else 0.0
        at = moment if str(moment).endswith("+08:00") else f"{moment}+08:00"
        hourly_out.append(
            {
                "at": at,
                "windLevel": beaufort_level(wind_ms),
                "rhPct": int(round(float(humidity))),
            }
        )

    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    mins = daily.get("temperature_2m_min") or []
    maxs = daily.get("temperature_2m_max") or []

    daily_out: list[dict[str, Any]] = []
    for index, day in enumerate(dates[:3]):
        min_t = float(mins[index]) if index < len(mins) and mins[index] is not None else 0.0
        max_t = float(maxs[index]) if index < len(maxs) and maxs[index] is not None else min_t
        daily_out.append(
            {
                "date": day,
                "minT": min_t,
                "avgT": round((min_t + max_t) / 2, 1),
            }
        )

    return {
        "plotNo": plot_no,
        "version": WEATHER_VERSION,
        "publishedAt": _published_at(),
        "hourly": hourly_out,
        "daily": daily_out,
    }


def fetch_forecast(
    plot_no: str,
    *,
    logger: Any = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    latitude, longitude = coordinates_for(plot_no)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "daily": "temperature_2m_min,temperature_2m_max",
        "forecast_days": 3,
        "timezone": "Asia/Shanghai",
        "wind_speed_unit": "ms",
    }
    try:
        response = httpx.get(OPENMETEO_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 - 任何网络/解析异常都触发降级
        _log_degraded(logger, plot_no, type(exc).__name__)
        raise
    return _map(plot_no, payload)