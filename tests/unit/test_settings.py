from __future__ import annotations

from pathlib import Path

import pytest

from sdk.settings import CipmSettings, SettingsError

ROOT = Path(__file__).resolve().parents[2]


def test_default_values(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(__import__("os").environ):
        if key.startswith("CIPM_"):
            monkeypatch.delenv(key, raising=False)
    settings = CipmSettings.from_env(tmp_path / "absent.env")
    assert settings.runtime == "local"
    assert settings.mock is True
    assert settings.api_port == 8000
    assert settings.ui_port == 8501
    assert settings.audit_retention_days == 730
    assert settings.mock_seed == 20261113
    assert settings.db_url == "sqlite:///./data/cipm.db"


def test_non_mock_missing_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CIPM_MOCK", "0")
    monkeypatch.delenv("CIPM_AGENTARTS_ENDPOINT", raising=False)
    monkeypatch.delenv("CIPM_LLM_ENDPOINT", raising=False)
    monkeypatch.delenv("CIPM_LLM_MODEL", raising=False)
    with pytest.raises(SettingsError) as excinfo:
        CipmSettings.from_env(tmp_path / "absent.env")
    message = str(excinfo.value)
    assert "CIPM_AGENTARTS_ENDPOINT" in message
    assert "CIPM_LLM_ENDPOINT" in message
    assert "http://" not in message


def test_sensitive_masking(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CIPM_LLM_API_KEY", "sk-very-secret-value")
    settings = CipmSettings.from_env(tmp_path / "absent.env")
    text = repr(settings)
    assert "sk-very-secret-value" not in text
    assert settings.llm_api_key == "sk-very-secret-value"
    assert settings.masked("llm_api_key") == "***"
    assert settings.masked("llm_model") == ""


def test_env_example_keys_match_settings() -> None:
    keys = {
        line.split("=", 1)[0].strip()
        for line in (ROOT / "ops" / "env.example").read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.strip().startswith("#")
    }
    assert keys == CipmSettings().env_keys