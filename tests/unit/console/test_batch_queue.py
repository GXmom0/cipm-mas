from __future__ import annotations

from apps.console.components.batch_queue import urgency_cell_color, _interpolate_color
from apps.console.theme import URGENCY_HEAT_HIGH, URGENCY_HEAT_LOW


def test_urgency_cell_color_min_value():
    color = urgency_cell_color(1, 1, 5)
    assert color == URGENCY_HEAT_LOW


def test_urgency_cell_color_max_value():
    color = urgency_cell_color(5, 1, 5)
    assert color == URGENCY_HEAT_HIGH


def test_urgency_cell_color_middle_value():
    color = urgency_cell_color(3, 1, 5)
    ratio = (3 - 1) / (5 - 1)
    expected = _interpolate_color(URGENCY_HEAT_LOW, URGENCY_HEAT_HIGH, ratio)
    assert color == expected


def test_urgency_cell_color_equal_min_max():
    color = urgency_cell_color(3, 3, 3)
    assert color == URGENCY_HEAT_LOW