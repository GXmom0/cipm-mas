from __future__ import annotations

import pytest

from mock.loader import plot_bundle


@pytest.fixture(scope="module", autouse=True)
def prepared_datasets() -> None:
    from mock.cli import write_all

    write_all()


def test_normal_plot_bundle_matches_mock() -> None:
    bundle = plot_bundle("PLOT-0912")
    prescription = bundle["prescription"]
    assert prescription is not None
    assert prescription["status"] == "pending_review"
    zone = next(item for item in prescription["zones"] if not item["zeroApplication"])
    assert zone["product"]["category"] == {"aiName": "啶虫脒", "formulation": "乳油"}
    assert zone["product"]["registryItemNo"] == "XJ-ACE-0381"
    assert zone["doseMlPerMu"] == 12.0
    assert zone["sprayVolumeLPerMu"] == 1.6
    assert prescription["safetyCheck"]["bufferDays"] == 13
    assert prescription["safetyCheck"]["remainingDays"] == 20
    assert prescription["registrySnapshot"]["version"] == "XJ-REG-2026.11.01"
    assert prescription["windowCheck"]["conclusion"] == "pass"
    assert bundle["calendar"]["phenology"] == "flower_boll"


def test_blocked_plot_has_no_prescription() -> None:
    bundle = plot_bundle("PLOT-0913")
    assert bundle["prescription"] is None
    assert bundle["stressResult"]["taskBlock"]["status"] == "blocked_pending_review"


def test_conflict_plot_is_refused() -> None:
    bundle = plot_bundle("PLOT-0914")
    safety = bundle["prescription"]["safetyCheck"]
    assert safety["conclusion"] == "refused"
    assert safety["bufferDays"] == -2
    assert safety["conflictProduct"] is not None


def test_rescheduled_plot_is_approved() -> None:
    bundle = plot_bundle("PLOT-0916")
    assert bundle["prescription"]["status"] == "approved"
    assert bundle["workOrder"]["status"] == "rescheduled"
    assert bundle["workOrder"]["windowCheckRef"]["verdict"] == "fail"


def test_unknown_plot_raises() -> None:
    with pytest.raises(KeyError):
        plot_bundle("PLOT-NOT-EXIST")