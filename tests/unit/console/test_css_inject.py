from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.console.components import css_inject


def test_inject_custom_css_no_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = []
    fake = SimpleNamespace(markdown=lambda content, unsafe_allow_html=False: captured.append(content))
    monkeypatch.setattr(css_inject, "st", fake)
    css_inject.inject_custom_css()
    assert len(captured) == 1


def test_inject_custom_css_contains_key_styles(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = []
    fake = SimpleNamespace(markdown=lambda content, unsafe_allow_html=False: captured.append(content))
    monkeypatch.setattr(css_inject, "st", fake)
    css_inject.inject_custom_css()
    css_content = captured[0]
    assert "stage-progress-container" in css_content
    assert "stage-node" in css_content
    assert "badge-pill" in css_content
    assert "cipm-table" in css_content
    assert "row-blocked" in css_content
    assert "metric-card" in css_content