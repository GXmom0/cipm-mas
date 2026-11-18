from __future__ import annotations

from domain.rules.work_window import (
    FAIL_MESSAGE,
    WorkWindowInput,
    evaluate_work_window,
)

PASS_MIN = (13.6, 13.2, 13.8)
PASS_AVG = (24.8, 24.2, 25.1)
CALM_WIND = tuple(2 if index % 5 else 3 for index in range(72))


def test_plot_0916_temperature_fails() -> None:
    result = evaluate_work_window(
        WorkWindowInput(
            min_temperatures=(11.8, 12.1, 12.6),
            avg_temperatures=(22.4, 22.9, 23.4),
            wind_levels=CALM_WIND,
            region="south",
            afternoon_humidity_pct=34.0,
        )
    )
    assert result.passed is False
    assert result.conclusion == "fail"
    assert result.message == FAIL_MESSAGE
    assert any("11.8" in item for item in result.violations)
    assert any("22.4" in item for item in result.violations)
    assert result.min_temperature == 11.8


def test_wind_red_line_fails() -> None:
    result = evaluate_work_window(
        WorkWindowInput(
            min_temperatures=PASS_MIN,
            avg_temperatures=PASS_AVG,
            wind_levels=(2, 4, 3),
        )
    )
    assert result.passed is False
    assert any("4 级" in item for item in result.violations)


def test_data_unavailable_fails() -> None:
    result = evaluate_work_window(
        WorkWindowInput(
            min_temperatures=(),
            avg_temperatures=(),
            wind_levels=(),
            data_available=False,
        )
    )
    assert result.passed is False
    assert "数据不可用" in result.violations[0]


def test_normal_window_passes() -> None:
    result = evaluate_work_window(
        WorkWindowInput(
            min_temperatures=PASS_MIN,
            avg_temperatures=PASS_AVG,
            wind_levels=CALM_WIND,
            region="south",
            afternoon_humidity_pct=34.0,
        )
    )
    assert result.passed is True
    assert result.conclusion == "pass"
    assert result.notices == ()


def test_south_low_humidity_adds_notice() -> None:
    result = evaluate_work_window(
        WorkWindowInput(
            min_temperatures=PASS_MIN,
            avg_temperatures=PASS_AVG,
            wind_levels=CALM_WIND,
            region="south",
            afternoon_humidity_pct=28.0,
        )
    )
    assert result.passed is True
    assert result.conclusion == "pass_with_mandatory_notice"
    assert "防漂移" in result.notices[0]


def test_north_low_humidity_no_notice() -> None:
    result = evaluate_work_window(
        WorkWindowInput(
            min_temperatures=PASS_MIN,
            avg_temperatures=PASS_AVG,
            wind_levels=CALM_WIND,
            region="north",
            afternoon_humidity_pct=28.0,
        )
    )
    assert result.passed is True
    assert result.conclusion == "pass"
    assert result.notices == ()