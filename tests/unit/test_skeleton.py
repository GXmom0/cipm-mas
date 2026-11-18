from __future__ import annotations

import importlib
import socket
from pathlib import Path

import pytest

from ops.start_dev import build_commands, parse_args, port_in_use
from sdk.settings import CipmSettings

ROOT = Path(__file__).resolve().parents[2]


def test_dependency_imports() -> None:
    for module in ("fastapi", "uvicorn", "pydantic", "httpx", "pytest"):
        assert importlib.import_module(module) is not None


def test_packages_importable() -> None:
    for package in ("apps", "agents", "domain", "adapters", "sdk", "mock"):
        assert importlib.import_module(package) is not None


def test_placeholder_readme_exists() -> None:
    expected = [
        ROOT / "agents" / "patrol" / "README.md",
        ROOT / "agents" / "decision" / "README.md",
        ROOT / "agents" / "execution" / "README.md",
        ROOT / "agents" / "assessment" / "README.md",
        ROOT / "knowledge" / "README.md",
        ROOT / "workflows" / "README.md",
        ROOT / "workflows" / "local" / "README.md",
        ROOT / "apps" / "window_service" / "README.md",
    ]
    for path in expected:
        assert path.exists(), path
        assert "M" in path.read_text(encoding="utf-8")


def test_no_network_blocks_connect(no_network) -> None:
    with pytest.raises(RuntimeError):
        socket.create_connection(("example.com", 80), timeout=1)


def test_fixed_clock(fixed_clock) -> None:
    assert fixed_clock.isoformat() == "2026-11-13T08:00:00+08:00"


def test_start_dev_args() -> None:
    args = parse_args(["--api-only", "--no-browser"])
    assert args.api_only is True
    assert args.ui_only is False
    settings = CipmSettings()
    commands = build_commands(settings, args)
    assert len(commands) == 1
    assert "uvicorn" in commands[0]
    assert port_in_use("127.0.0.1", 65535) is False