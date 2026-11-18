from __future__ import annotations

from apps.console.components.stress_chart import build_stress_data, STRESS_LEVELS


def test_build_stress_data_counts():
    plots = [
        {"plotNo": "P1", "stages": {"patrol": "已完成"}},
        {"plotNo": "P2", "stages": {"patrol": "已完成"}},
        {"plotNo": "P3", "stages": {"patrol": "阻断待复核"}},
        {"plotNo": "P4", "stages": {"patrol": "降级待确认"}},
        {"plotNo": "P5", "stages": {"patrol": "识别中"}},
    ]
    data = build_stress_data(plots)
    assert data["无"] == 2
    assert data["重度"] == 1
    assert data["中度"] == 1
    assert data["轻度"] == 1


def test_build_stress_data_all_none():
    plots = [
        {"plotNo": "P1", "stages": {"patrol": "已完成"}},
        {"plotNo": "P2", "stages": {"patrol": "已完成"}},
    ]
    data = build_stress_data(plots)
    assert data["无"] == 2
    assert data["轻度"] == 0
    assert data["中度"] == 0
    assert data["重度"] == 0


def test_build_stress_data_empty_plots():
    data = build_stress_data([])
    for level in STRESS_LEVELS:
        assert data[level] == 0