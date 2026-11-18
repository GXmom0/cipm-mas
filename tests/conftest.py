from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

FIXED_NOW = datetime(2026, 11, 13, 8, 0, 0, tzinfo=timezone(timedelta(hours=8)))


@pytest.fixture
def fixed_clock() -> datetime:
    return FIXED_NOW


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked_create_connection(address, *args, **kwargs):
        raise RuntimeError(f"测试环境禁止真实外部网络访问：{address}")

    monkeypatch.setattr(socket, "create_connection", _blocked_create_connection)
    try:
        import httpx
    except ImportError:
        return

    def _blocked_handle(self, request):
        raise RuntimeError("测试环境禁止真实 HTTP 调用")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _blocked_handle)


@pytest.fixture
def datasets_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "mock" / "datasets"