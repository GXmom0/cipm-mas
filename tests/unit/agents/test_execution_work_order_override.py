from __future__ import annotations

import pytest

from agents.execution.agent import ExecutionAgent
from agents.execution.window_guard import evaluate_for_plot
from mock.loader import plot_bundle
from mock.seed import iso_after

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


def _prescription(plot_no: str):
    return plot_bundle(plot_no)["prescription"]


def _passing_agent() -> ExecutionAgent:
    return ExecutionAgent(
        window_evaluator=lambda plot_no, region: evaluate_for_plot(plot_no, region, PASS_FORECAST)
    )


def test_explicit_work_order_no_overrides_command_and_receipt() -> None:
    outcome = _passing_agent().dispatch(
        "PLOT-0916", _prescription("PLOT-0916"), work_order_no="WO-CUSTOM-001"
    )

    assert outcome.status == "dispatched"
    assert outcome.work_order_no == "WO-CUSTOM-001"
    assert outcome.command["workOrderNo"] == "WO-CUSTOM-001"
    assert outcome.receipt["workOrderNo"] == "WO-CUSTOM-001"


def test_default_work_order_no_unchanged_when_absent_or_blank() -> None:
    default = _passing_agent().dispatch("PLOT-0916", _prescription("PLOT-0916"))
    none_arg = _passing_agent().dispatch("PLOT-0916", _prescription("PLOT-0916"), work_order_no=None)
    blank_arg = _passing_agent().dispatch("PLOT-0916", _prescription("PLOT-0916"), work_order_no="")

    assert default.work_order_no == none_arg.work_order_no == blank_arg.work_order_no
    assert default.work_order_no != ""
    assert blank_arg.command["workOrderNo"] == default.work_order_no
    assert blank_arg.receipt["workOrderNo"] == default.work_order_no