from __future__ import annotations

from apps.console.components.compliance_icon import (
    SAFETY_ICON_MAP,
    WINDOW_ICON_MAP,
)


def test_safety_icon_satisfied():
    icon, color = SAFETY_ICON_MAP["satisfied"]
    assert icon == "✅"
    assert color == "#4CAF50"


def test_safety_icon_degraded():
    icon, color = SAFETY_ICON_MAP["degraded"]
    assert icon == "⚠️"
    assert color == "#F57C00"


def test_safety_icon_refused():
    icon, color = SAFETY_ICON_MAP["refused"]
    assert icon == "❌"
    assert color == "#D32F2F"


def test_window_icon_pass():
    icon, color = WINDOW_ICON_MAP["pass"]
    assert icon == "✅"
    assert color == "#4CAF50"


def test_window_icon_pass_with_notice():
    icon, color = WINDOW_ICON_MAP["pass_with_mandatory_notice"]
    assert icon == "⚠️"
    assert color == "#F57C00"


def test_window_icon_fail():
    icon, color = WINDOW_ICON_MAP["fail"]
    assert icon == "❌"
    assert color == "#D32F2F"