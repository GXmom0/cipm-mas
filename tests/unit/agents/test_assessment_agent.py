from __future__ import annotations

import pytest

from agents.assessment.agent import AssessmentAgent
from mock.loader import plot_bundle
from mock.seed import iso_after
from sdk.contracts.assessment import AssessmentPayload


@pytest.fixture(scope="module", autouse=True)
def prepared_datasets() -> None:
    from mock.cli import write_all

    write_all()


def _result(levels: list[str], result_no: str = "SR-TEST-0001") -> dict:
    return {
        "resultNo": result_no,
        "resultVersion": 1,
        "orthophoto": {"sortieNo": "FL-20261115-001"},
        "partitions": [
            {"partitionNo": f"Z{index + 1:02d}", "stressLevel": level}
            for index, level in enumerate(levels)
        ],
    }


def _feedback(coverage: float = 97.5) -> dict:
    return {
        "workOrderNo": "WO-TEST-0001",
        "coveragePct": coverage,
        "completedAt": iso_after(days=1, hours=3),
    }


def _prescription() -> dict:
    return plot_bundle("PLOT-0912")["prescription"]


def test_assessment_computes_qualified_result() -> None:
    outcome = AssessmentAgent().assess(
        "PLOT-0912",
        before_result=_result(["heavy", "heavy", "medium"]),
        after_result=_result(["medium", "light", "none"], "SR-TEST-0001-recheck"),
        feedback=_feedback(),
        prescription=_prescription(),
    )
    assert outcome.coverage_pct == 97.5
    assert outcome.suppression_rate == 0.625
    assert outcome.verdict == "qualified"
    assert outcome.qualified is True
    assert outcome.recommended_action == "continue"
    AssessmentPayload.model_validate(outcome.payload)


def test_assessment_flags_severe_deviation() -> None:
    outcome = AssessmentAgent().assess(
        "PLOT-0912",
        before_result=_result(["heavy", "medium", "light"]),
        after_result=_result(["heavy", "medium", "none"], "SR-TEST-0001-recheck"),
        feedback=_feedback(),
        prescription=_prescription(),
    )
    assert outcome.verdict == "not_qualified"
    assert "Z01" in outcome.severe_zones
    assert outcome.recommended_action == "manual_expert"


def test_low_coverage_requires_recheck() -> None:
    outcome = AssessmentAgent().assess(
        "PLOT-0912",
        before_result=_result(["heavy", "heavy", "medium"]),
        after_result=_result(["medium", "light", "none"], "SR-TEST-0001-recheck"),
        feedback=_feedback(coverage=90.0),
        prescription=_prescription(),
    )
    assert outcome.verdict == "not_qualified"
    assert outcome.recommended_action == "recheck"


def test_zero_baseline_has_zero_suppression() -> None:
    outcome = AssessmentAgent().assess(
        "PLOT-0912",
        before_result=_result(["none", "none"]),
        after_result=_result(["none", "none"], "SR-TEST-0001-recheck"),
        feedback=_feedback(),
        prescription=_prescription(),
    )
    assert outcome.suppression_rate == 0.0
    assert outcome.verdict == "not_qualified"