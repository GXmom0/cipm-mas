from __future__ import annotations

import pytest

from domain.models.enums import SafetyConclusion
from domain.rules import CompoundComponent, SafetyIntervalInput, check_single_agent, evaluate_safety_interval
from mock.cli import write_all
from mock.loader import load_all, load_scenario


@pytest.fixture(scope="module", autouse=True)
def prepared_datasets() -> None:
    write_all()


def _prescription(plot_no: str) -> dict:
    for dataset in load_all():
        expected = dataset["expected"].get(plot_no)
        if not expected:
            continue
        for prescription in dataset["prescriptions"]:
            if prescription["safetyCheck"]["remainingDays"] == expected["remainingDays"]:
                return prescription
    raise AssertionError(f"未找到地块 {plot_no} 的处方")


def test_m01_three_scenarios_loaded() -> None:
    datasets = load_all()
    assert len(datasets) == 3
    plot_nos = {plot["plotNo"] for dataset in datasets for plot in dataset["plots"]}
    assert plot_nos == {"PLOT-0912", "PLOT-0913", "PLOT-0914", "PLOT-0915", "PLOT-0916"}


def test_m02_rule_matches_normal_plot() -> None:
    prescription = _prescription("PLOT-0912")
    check = prescription["safetyCheck"]
    result = evaluate_safety_interval(
        SafetyIntervalInput(
            remaining_days=check["remainingDays"], safety_interval_days=check["safetyIntervalDays"]
        )
    )
    assert result.conclusion == SafetyConclusion.SATISFIED.value
    assert result.buffer_days == 13 == check["bufferDays"]


def test_m03_rule_matches_degraded_plot() -> None:
    prescription = _prescription("PLOT-0915")
    check = prescription["safetyCheck"]
    result = evaluate_safety_interval(
        SafetyIntervalInput(
            remaining_days=check["remainingDays"], safety_interval_days=check["safetyIntervalDays"]
        )
    )
    assert result.conclusion == SafetyConclusion.DEGRADED.value
    assert [reason.value for reason in result.degrade_reasons] == ["BUFFER_LT_3"]
    assert check["bufferDays"] == 2


def test_m04_rule_matches_conflict_plot() -> None:
    prescription = _prescription("PLOT-0914")
    check = prescription["safetyCheck"]
    result = evaluate_safety_interval(
        SafetyIntervalInput(
            remaining_days=check["remainingDays"],
            safety_interval_days=check["safetyIntervalDays"],
            conflict_product=None,
        )
    )
    assert result.conclusion == SafetyConclusion.REFUSED.value
    assert result.buffer_days == -2 == check["bufferDays"]


def test_m05_single_agent_zones() -> None:
    for dataset in load_all():
        for prescription in dataset["prescriptions"]:
            for zone in prescription["zones"]:
                if zone["zeroApplication"]:
                    continue
                product = zone["product"]
                component = CompoundComponent(
                    ai_name=product["category"]["aiName"],
                    formulation=product["category"]["formulation"],
                    registry_item_no=product["registryItemNo"],
                    safety_interval_days=zone["safetyIntervalDays"],
                )
                result = check_single_agent((component,))
                assert result.allowed is True
                assert result.detected is False


def test_m06_blocked_plot_has_no_prescription() -> None:
    dataset = load_scenario("low_confidence_plot")
    assert dataset["stressResults"][0]["taskBlock"]["status"] == "blocked_pending_review"
    assert dataset["prescriptions"] == []