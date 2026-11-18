from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

_TRUE = {"1", "true", "yes", "y", "on"}
_FALSE = {"0", "false", "no", "n", "off"}
_SENSITIVE_MARKS = ("key", "secret", "token", "password")
_REQUIRED_WHEN_NOT_MOCK = (
    "CIPM_AGENTARTS_ENDPOINT",
    "CIPM_LLM_ENDPOINT",
    "CIPM_LLM_MODEL",
)


class SettingsError(RuntimeError):
    pass


def load_env_file(path: str | Path = ".env") -> dict[str, str]:
    target = Path(path)
    if not target.exists():
        return {}
    result: dict[str, str] = {}
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def _as_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise SettingsError("布尔型配置取值非法：CIPM_MOCK")


@dataclass(frozen=True)
class CipmSettings:
    runtime: str = "local"
    mock: bool = True
    api_base: str = "http://127.0.0.1:8000"
    api_port: int = 8000
    ui_port: int = 8501
    idempotency_ttl_seconds: int = 600
    registry_source: str = "mock"
    weather_provider: str = "mock"
    audit_dir: str = "./data/audit"
    data_dir: str = "./data"
    db_url: str = "sqlite:///./data/cipm.db"
    audit_retention_days: int = 730
    mock_seed: int = 20261113
    log_level: str = "INFO"
    agentarts_endpoint: str = ""
    llm_endpoint: str = ""
    llm_model: str = ""
    llm_api_key: str = ""
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.2
    agentarts_project_id: str = ""
    image_oss_endpoint: str = ""
    image_oss_bucket: str = ""
    mqtt_broker: str = ""
    mqtt_topic_sensor: str = ""
    mqtt_topic_actuator: str = ""
    device_rest_endpoint: str = ""
    weather_endpoint: str = ""
    calendar_endpoint: str = ""
    registry_endpoint: str = ""

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> "CipmSettings":
        file_values = load_env_file(env_file)

        def read(name: str) -> str:
            env_key = f"CIPM_{name.upper()}"
            if env_key in os.environ:
                return os.environ[env_key]
            return file_values.get(env_key, "")

        def read_int(name: str, default: int) -> int:
            raw = read(name)
            if raw == "":
                return default
            try:
                return int(raw)
            except ValueError as exc:
                raise SettingsError(f"整型配置取值非法：CIPM_{name.upper()}") from exc

        def read_float(name: str, default: float) -> float:
            raw = read(name)
            if raw == "":
                return default
            try:
                return float(raw)
            except ValueError as exc:
                raise SettingsError(f"浮点型配置取值非法：CIPM_{name.upper()}") from exc

        settings = cls(
            runtime=read("runtime") or "local",
            mock=_as_bool(read("mock") or "1"),
            api_base=read("api_base") or "http://127.0.0.1:8000",
            api_port=read_int("api_port", 8000),
            ui_port=read_int("ui_port", 8501),
            idempotency_ttl_seconds=read_int("idempotency_ttl_seconds", 600),
            registry_source=read("registry_source") or "mock",
            weather_provider=read("weather_provider") or "mock",
            audit_dir=read("audit_dir") or "./data/audit",
            data_dir=read("data_dir") or "./data",
            db_url=read("db_url") or "sqlite:///./data/cipm.db",
            audit_retention_days=read_int("audit_retention_days", 730),
            mock_seed=read_int("mock_seed", 20261113),
            log_level=read("log_level") or "INFO",
            agentarts_endpoint=read("agentarts_endpoint"),
            llm_endpoint=read("llm_endpoint"),
            llm_model=read("llm_model"),
            llm_api_key=read("llm_api_key"),
            llm_timeout_seconds=read_float("llm_timeout_seconds", 30.0),
            llm_max_retries=read_int("llm_max_retries", 2),
            llm_temperature=read_float("llm_temperature", 0.2),
            agentarts_project_id=read("agentarts_project_id"),
            image_oss_endpoint=read("image_oss_endpoint"),
            image_oss_bucket=read("image_oss_bucket"),
            mqtt_broker=read("mqtt_broker"),
            mqtt_topic_sensor=read("mqtt_topic_sensor"),
            mqtt_topic_actuator=read("mqtt_topic_actuator"),
            device_rest_endpoint=read("device_rest_endpoint"),
            weather_endpoint=read("weather_endpoint"),
            calendar_endpoint=read("calendar_endpoint"),
            registry_endpoint=read("registry_endpoint"),
        )
        if not settings.mock:
            missing = [key for key in _REQUIRED_WHEN_NOT_MOCK if not read(key.removeprefix("CIPM_").lower())]
            if missing:
                raise SettingsError("非 Mock 模式缺少必需配置：" + "、".join(missing))
        return settings

    @property
    def env_keys(self) -> set[str]:
        return {f"CIPM_{field.name.upper()}" for field in fields(self)}

    @property
    def sensitive_fields(self) -> tuple[str, ...]:
        return tuple(
            field.name
            for field in fields(self)
            if any(mark in field.name for mark in _SENSITIVE_MARKS)
        )

    def masked(self, name: str) -> str:
        value = getattr(self, name)
        if name in self.sensitive_fields:
            return "***" if value else ""
        return str(value)

    def __repr__(self) -> str:
        body = ", ".join(f"{field.name}={self.masked(field.name)!r}" for field in fields(self))
        return f"CipmSettings({body})"


def get_settings(env_file: str | Path = ".env") -> CipmSettings:
    return CipmSettings.from_env(env_file)