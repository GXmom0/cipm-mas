from __future__ import annotations

import pytest

from mock.seed import iso_after
from workflows.local.pipeline import run_pipeline

PASS_FORECAST = {
    "daily": [
        {"date": "2026-11-13", "minT": 13.6, "avgT": 24.8},
        {"date": "2026-11-14", "minT": 13.2, "avgT": 24.2},
        {"date": "2026-11-15", "minT": 13.8, "avgT": 25.1},
    ],
    "hourly": [
        {"at": iso_after(hours=hour), "windLevel": 2 if hour % 5 else 3, "rhPct": 34}
        for hour in range(48)
    ],
}


@pytest.fixture(scope="module", autouse=True)
def prepared_datasets() -> None:
    from mock.cli import write_all

    write_all()


def test_blocked_plot_stops_downstream_agents() -> None:
    result = run_pipeline("PLOT-0913")
    assert result.stages["patrol"] == "阻断待复核"
    assert result.stages["prescription"] == "已阻断"
    assert result.decision is None
    assert result.execution is None
    assert result.assessment is None
    assert "待人工复核" in result.note
    assert result.patrol["blockingPartitions"] == ["Z03"]


def test_window_failure_stops_at_execution() -> None:
    result = run_pipeline("PLOT-0916")
    assert result.stages["patrol"] == "已完成"
    assert result.stages["prescription"] == "已通过"
    assert result.stages["execution"] == "待重新排期"
    assert result.stages["assessment"] == "未开始"
    assert result.execution["status"] == "rescheduled"
    assert result.assessment is None
    assert "作业窗口校验不通过" in result.note


def test_passing_window_runs_all_four_stages() -> None:
    result = run_pipeline("PLOT-0916", forecast=PASS_FORECAST)
    assert result.stages["patrol"] == "已完成"
    assert result.stages["prescription"] == "已通过"
    assert result.stages["execution"] == "已下发"
    assert result.stages["assessment"] in {"达标", "未达标"}
    assert result.assessment is not None
    assert result.assessment["coveragePct"] == 97.5
    assert result.completed is True