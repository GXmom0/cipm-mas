from __future__ import annotations

import pytest

from agents.execution.agent import ExecutionAgent
from agents.execution.window_guard import evaluate_for_plot
from mock.loader import plot_bundle
from mock.seed import iso_after
from sdk.contracts.dispatch import DispatchCommand

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


def test_plot_0916_window_failure_reschedules_without_dispatch() -> None:
    outcome = ExecutionAgent().dispatch("PLOT-0916", _prescription("PLOT-0916"))
    assert outcome.status == "rescheduled"
    assert outcome.dispatched is False
    assert outcome.command is None
    assert outcome.receipt is None
    assert outcome.message == "作业窗口校验不通过，转待重新排期"
    assert any("11.8" in item for item in outcome.violations)


def test_unapproved_prescription_is_rejected() -> None:
    outcome = ExecutionAgent().dispatch("PLOT-0912", _prescription("PLOT-0912"))
    assert outcome.status == "rejected"
    assert outcome.command is None
    assert outcome.receipt is None


def test_approved_prescription_dispatches_when_window_passes() -> None:
    agent = ExecutionAgent(
        window_evaluator=lambda plot_no, region: evaluate_for_plot(
            plot_no, region, PASS_FORECAST
        )
    )
    outcome = agent.dispatch("PLOT-0916", _prescription("PLOT-0916"))
    assert outcome.status == "dispatched"
    assert outcome.command is not None
    DispatchCommand.model_validate(outcome.command)
    assert outcome.command["windowCheckRef"]["checkNo"].startswith("WC-E-")
    assert outcome.receipt["accepted"] is True
    assert "下发成功" not in outcome.message


def test_device_rejection_reschedules() -> None:
    from sdk.contracts.dispatch import DispatchReceipt

    def rejecting_device(command, device_no="DEV-XJ-01"):
        return DispatchReceipt(
            receiptNo="RC-TEST",
            workOrderNo=command["workOrderNo"],
            deviceNo=device_no,
            accepted=False,
            acceptedAt=iso_after(minutes=1),
            message="设备拒绝",
        )

    agent = ExecutionAgent(
        window_evaluator=lambda plot_no, region: evaluate_for_plot(
            plot_no, region, PASS_FORECAST
        ),
        device=rejecting_device,
    )
    outcome = agent.dispatch("PLOT-0916", _prescription("PLOT-0916"))
    assert outcome.status == "rescheduled"
    assert outcome.receipt["accepted"] is False