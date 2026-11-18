from __future__ import annotations

import pytest

from domain.models.enums import DegradeReason, Phenology, SafetyConclusion, Toxicity
from domain.rules import (
    RULE_VERSION,
    ProductRef,
    RuleInputError,
    SafetyCandidate,
    SafetyIntervalInput,
    check_single_agent,
    evaluate_safety_interval,
)

PRODUCT = ProductRef(registry_item_no="XJ-ACE-0381", ai_name="啶虫脒", formulation="乳油")


def _candidate(item_no: str, interval: int, toxicity: Toxicity = Toxicity.LOW) -> SafetyCandidate:
    return SafetyCandidate(
        registry_item_no=item_no,
        ai_name="吡虫啉",
        formulation="可湿性粉剂",
        safety_interval_days=interval,
        dose_range_ml_per_mu=(8.0, 16.0),
        toxicity=toxicity,
    )


def test_st01_satisfied() -> None:
    result = evaluate_safety_interval(SafetyIntervalInput(remaining_days=10, safety_interval_days=7))
    assert result.conclusion == SafetyConclusion.SATISFIED.value
    assert result.buffer_days == 3
    assert result.degrade_reasons == ()


def test_st02_refused_when_interval_exceeds() -> None:
    result = evaluate_safety_interval(
        SafetyIntervalInput(remaining_days=5, safety_interval_days=7, conflict_product=PRODUCT)
    )
    assert result.conclusion == SafetyConclusion.REFUSED.value
    assert result.buffer_days == -2
    assert result.conflict_product == PRODUCT
    assert result.reason_code == "INTERVAL_EXCEEDS_REMAINING"
    assert "距预计采收 5 天" in result.message
    assert "安全间隔期 7 天" in result.message
    assert "啶虫脒·乳油" in result.message
    assert "可选替代" in result.message


def test_st03_degraded_buffer_lt_3() -> None:
    result = evaluate_safety_interval(SafetyIntervalInput(remaining_days=9, safety_interval_days=7))
    assert result.conclusion == SafetyConclusion.DEGRADED.value
    assert result.degrade_reasons == (DegradeReason.BUFFER_LT_3,)
    assert result.requires_expert_confirm is True


def test_st04_buffer_zero() -> None:
    result = evaluate_safety_interval(SafetyIntervalInput(remaining_days=3, safety_interval_days=3))
    assert result.conclusion == SafetyConclusion.DEGRADED.value
    assert result.degrade_reasons == (DegradeReason.BUFFER_LT_3,)


def test_st05_no_eligible_item() -> None:
    result = evaluate_safety_interval(
        SafetyIntervalInput(
            remaining_days=5,
            safety_interval_days=7,
            candidates=(_candidate("XJ-A", 7), _candidate("XJ-B", 10)),
            conflict_product=PRODUCT,
        )
    )
    assert result.conclusion == SafetyConclusion.REFUSED.value
    assert result.reason_code == "NO_ELIGIBLE_ITEM"
    assert "安全间隔期 7 天" in result.message


def test_st06_reuse_within_interval() -> None:
    result = evaluate_safety_interval(
        SafetyIntervalInput(
            remaining_days=20,
            safety_interval_days=7,
            same_ai_used_within_interval=True,
            conflict_product=PRODUCT,
        )
    )
    assert result.conclusion == SafetyConclusion.REFUSED.value
    assert result.reason_code == "REUSE_WITHIN_INTERVAL"


def test_st07_season_limit() -> None:
    result = evaluate_safety_interval(
        SafetyIntervalInput(
            remaining_days=20,
            safety_interval_days=7,
            season_usage_exceeded=True,
            conflict_product=PRODUCT,
        )
    )
    assert result.conclusion == SafetyConclusion.REFUSED.value
    assert result.reason_code == "SEASON_LIMIT_REACHED"


def test_st08_rotation_interval() -> None:
    result = evaluate_safety_interval(
        SafetyIntervalInput(
            remaining_days=10,
            safety_interval_days=7,
            days_since_last_same_ai=5,
            rotation_interval_days=10,
        )
    )
    assert result.conclusion == SafetyConclusion.DEGRADED.value
    assert DegradeReason.ROTATION_INTERVAL in result.degrade_reasons


def test_st09_pre_harvest_sensitive() -> None:
    result = evaluate_safety_interval(
        SafetyIntervalInput(remaining_days=10, safety_interval_days=7, pre_harvest_sensitive=True)
    )
    assert result.conclusion == SafetyConclusion.DEGRADED.value
    assert DegradeReason.PRE_HARVEST_SENSITIVE in result.degrade_reasons


def test_st10_seedling_low_risk() -> None:
    result = evaluate_safety_interval(
        SafetyIntervalInput(
            remaining_days=30, safety_interval_days=7, phenology=Phenology.SEEDLING
        )
    )
    assert result.conclusion == SafetyConclusion.DEGRADED.value
    assert result.degrade_reasons == (DegradeReason.PHENOLOGY_LOW_RISK,)
    assert result.requires_expert_confirm is True


def test_st11_zero_remaining_days() -> None:
    result = evaluate_safety_interval(
        SafetyIntervalInput(remaining_days=0, safety_interval_days=1, conflict_product=PRODUCT)
    )
    assert result.conclusion == SafetyConclusion.REFUSED.value


@pytest.mark.parametrize("remaining", range(0, 31))
@pytest.mark.parametrize("interval", [1, 3, 5, 7, 10, 15, 30])
def test_st12_all_combinations(remaining: int, interval: int) -> None:
    result = evaluate_safety_interval(
        SafetyIntervalInput(
            remaining_days=remaining,
            safety_interval_days=interval,
            conflict_product=PRODUCT,
        )
    )
    assert result.conclusion in {
        SafetyConclusion.SATISFIED.value,
        SafetyConclusion.DEGRADED.value,
        SafetyConclusion.REFUSED.value,
    }
    assert result.buffer_days == remaining - interval
    if remaining < interval:
        assert result.conclusion == SafetyConclusion.REFUSED.value
    elif remaining - interval >= 3:
        assert result.conclusion == SafetyConclusion.SATISFIED.value


@pytest.mark.parametrize(
    "remaining, interval",
    [(10, 0), (10, 31), (-1, 7)],
)
def test_st13_invalid_input(remaining: int, interval: int) -> None:
    with pytest.raises(RuleInputError) as excinfo:
        SafetyIntervalInput(remaining_days=remaining, safety_interval_days=interval)
    assert excinfo.value.error_code == "CIPM-RULE-5005"


def test_st14_multiple_degrade_reasons() -> None:
    result = evaluate_safety_interval(
        SafetyIntervalInput(remaining_days=9, safety_interval_days=7, pre_harvest_sensitive=True)
    )
    assert result.degrade_reasons == (
        DegradeReason.BUFFER_LT_3,
        DegradeReason.PRE_HARVEST_SENSITIVE,
    )


def test_st15_package_exports() -> None:
    assert RULE_VERSION == "SAFETY-RULE-1.0"
    assert callable(evaluate_safety_interval)
    assert callable(check_single_agent)