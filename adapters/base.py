from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ImageOssAdapter(Protocol):
    def fetch_metadata(self, sortie_no: str) -> dict[str, Any]: ...

    def download(self, object_key: str) -> bytes: ...


@runtime_checkable
class SensorMqttAdapter(Protocol):
    def subscribe(self, topic: str) -> None: ...


@runtime_checkable
class WeatherAdapter(Protocol):
    def get_forecast(self, plot_no: str) -> dict[str, Any]: ...


@runtime_checkable
class CalendarAdapter(Protocol):
    def get(self, plot_no: str) -> dict[str, Any]: ...


@runtime_checkable
class RegistryAdapter(Protocol):
    def list_items(self, version: str | None = None) -> list[dict[str, Any]]: ...


@runtime_checkable
class DeviceRestAdapter(Protocol):
    def dispatch(self, command: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class NotifyAdapter(Protocol):
    def publish(self, event_type: str, payload: dict[str, Any]) -> None: ...