from __future__ import annotations

from domain.rules.prescription_guard import (
    NO_CALENDAR,
    NO_IRRIGATION,
    NO_REGISTRY,
    NO_WEATHER,
    STRESS_BLOCKED,
    STRESS_NOT_FROZEN,
    PrerequisiteInput,
    check_prerequisites,
)


def test_all_present_passes() -> None:
    result = check_prerequisites(PrerequisiteInput())
    assert result.allowed is True
    assert result.blocked is False
    assert result.missing_items == ()
    assert result.reason_codes == ()


def test_stress_blocked_rejects() -> None:
    result = check_prerequisites(PrerequisiteInput(block_status="blocked_pending_review"))
    assert result.blocked is True
    assert STRESS_BLOCKED in result.reason_codes


def test_stress_not_frozen_rejects() -> None:
    result = check_prerequisites(PrerequisiteInput(stress_result_version=None))
    assert result.blocked is True
    assert STRESS_NOT_FROZEN in result.reason_codes


def test_missing_materials_listed() -> None:
    result = check_prerequisites(
        PrerequisiteInput(
            has_irrigation=False,
            has_calendar=False,
            has_registry_snapshot=False,
            has_weather=False,
        )
    )
    assert result.blocked is True
    assert set(result.reason_codes) == {NO_IRRIGATION, NO_CALENDAR, NO_REGISTRY, NO_WEATHER}
    assert len(result.missing_items) == 4


def test_undetermined_stress_blocks() -> None:
    result = check_prerequisites(PrerequisiteInput(block_status="undetermined"))
    assert STRESS_BLOCKED in result.reason_codes