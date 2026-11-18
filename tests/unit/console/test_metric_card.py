from __future__ import annotations

from apps.console.components.metric_card import buffer_color
from apps.console.theme import BUFFER_DANGER_COLOR, BUFFER_SAFE_COLOR, BUFFER_WARNING_COLOR


def test_buffer_color_negative():
    assert buffer_color(-1) == BUFFER_DANGER_COLOR
    assert buffer_color(-5) == BUFFER_DANGER_COLOR


def test_buffer_color_zero_to_three():
    assert buffer_color(0) == BUFFER_WARNING_COLOR
    assert buffer_color(1) == BUFFER_WARNING_COLOR
    assert buffer_color(2) == BUFFER_WARNING_COLOR


def test_buffer_color_safe():
    assert buffer_color(3) == BUFFER_SAFE_COLOR
    assert buffer_color(10) == BUFFER_SAFE_COLOR