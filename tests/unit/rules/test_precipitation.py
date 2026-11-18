from __future__ import annotations

from domain.rules.work_window import (
    PrecipitationCheckInput,
    WorkWindowInput,
    check_precipitation_probability,
    evaluate_work_window,
)


def test_all_below_limit_passes() -> None:
    result = check_precipitation_probability(
        PrecipitationCheckInput(probabilities_pct=(10, 20, 25, 30, 5, 0))
    )
    assert result.passed is True
    assert result.conclusion == "pass"
    assert result.exceed_hours == ()


def test_one_exceeds_limit_fails() -> None:
    result = check_precipitation_probability(
        PrecipitationCheckInput(probabilities_pct=(10, 20, 45, 30, 5, 0))
    )
    assert result.passed is False
    assert result.conclusion == "fail"
    assert result.exceed_hours == (3,)
    assert any("45" in item for item in result.violations)


def test_values_echoed() -> None:
    values = (10, 20, 30, 40, 5, 0)
    result = check_precipitation_probability(PrecipitationCheckInput(probabilities_pct=values))
    assert result.probabilities_pct == values
    assert result.exceed_hours == (4,)


def test_missing_data_fails() -> None:
    result = check_precipitation_probability(
        PrecipitationCheckInput(probabilities_pct=(), data_available=False)
    )
    assert result.passed is False
    assert "缺失" in result.violations[0]


def test_insufficient_hours_fails() -> None:
    result = check_precipitation_probability(
        PrecipitationCheckInput(probabilities_pct=(10, 20, 30))
    )
    assert result.passed is False


def test_work_window_integrates_precipitation() -> None:
    result = evaluate_work_window(
        WorkWindowInput(
            min_temperatures=(13.6, 13.2, 13.8),
            avg_temperatures=(24.8, 24.2, 25.1),
            wind_levels=(2, 2, 2),
            region="south",
            afternoon_humidity_pct=34.0,
            precipitation_probabilities_pct=(10, 20, 45, 30, 5, 0),
        )
    )
    assert result.passed is False
    assert any("降水概率" in item for item in result.violations)