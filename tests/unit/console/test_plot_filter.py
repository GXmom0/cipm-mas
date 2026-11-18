from __future__ import annotations

from apps.console.components.plot_filter import filter_plots


def test_filter_by_search_plot_no():
    plots = [
        {"plotNo": "PLOT-0912", "plotName": "试验田A", "stages": {}, "badges": []},
        {"plotNo": "PLOT-0913", "plotName": "试验田B", "stages": {}, "badges": []},
    ]
    result = filter_plots(plots, "0912", [], [])
    assert len(result) == 1
    assert result[0]["plotNo"] == "PLOT-0912"


def test_filter_by_search_plot_name():
    plots = [
        {"plotNo": "PLOT-0912", "plotName": "试验田A", "stages": {}, "badges": []},
        {"plotNo": "PLOT-0913", "plotName": "试验田B", "stages": {}, "badges": []},
    ]
    result = filter_plots(plots, "试验田A", [], [])
    assert len(result) == 1
    assert result[0]["plotName"] == "试验田A"


def test_filter_by_stage():
    plots = [
        {"plotNo": "PLOT-0912", "plotName": "A", "stages": {"patrol": "已完成"}, "badges": []},
        {"plotNo": "PLOT-0913", "plotName": "B", "stages": {"patrol": "阻断待复核"}, "badges": []},
    ]
    result = filter_plots(plots, "", ["阻断待复核"], [])
    assert len(result) == 1
    assert result[0]["plotNo"] == "PLOT-0913"


def test_filter_by_badge():
    plots = [
        {"plotNo": "PLOT-0912", "plotName": "A", "stages": {}, "badges": ["BLOCKED"]},
        {"plotNo": "PLOT-0913", "plotName": "B", "stages": {}, "badges": ["DEGRADED"]},
    ]
    result = filter_plots(plots, "", [], ["BLOCKED"])
    assert len(result) == 1
    assert result[0]["plotNo"] == "PLOT-0912"


def test_filter_no_conditions_returns_all():
    plots = [
        {"plotNo": "PLOT-0912", "plotName": "A", "stages": {}, "badges": []},
        {"plotNo": "PLOT-0913", "plotName": "B", "stages": {}, "badges": []},
    ]
    result = filter_plots(plots, "", [], [])
    assert len(result) == 2