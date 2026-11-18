from __future__ import annotations

import json

from domain.models.enums import (
    ALL_ENUM_VALUES,
    LABELS_ZH,
    BadgeCode,
    DegradeReason,
    Phenology,
    PrescriptionStatus,
    SafetyConclusion,
    StressLevel,
    StressType,
)


def test_enum_values_match_design() -> None:
    assert {item.value for item in StressLevel} == {"none", "light", "medium", "heavy"}
    assert {item.value for item in StressType} == {
        "pest_disease",
        "nutrient_deficiency",
        "drought",
        "waterlogging",
        "undetermined",
    }
    assert {item.value for item in SafetyConclusion} == {"satisfied", "degraded", "refused"}
    assert {item.value for item in DegradeReason} == {
        "BUFFER_LT_3",
        "ROTATION_INTERVAL",
        "PRE_HARVEST_SENSITIVE",
        "PHENOLOGY_LOW_RISK",
    }
    assert {item.value for item in Phenology} == {
        "seedling",
        "bud",
        "flower_boll",
        "boll_opening",
    }
    assert {item.value for item in PrescriptionStatus} == {
        "draft",
        "pending_window",
        "degraded_pending_confirm",
        "pending_review",
        "approved",
        "rejected",
        "refused",
    }
    assert {item.value for item in BadgeCode} == {"BLOCKED", "DEGRADED", "REFUSED", "RESCHEDULED"}


def test_labels_cover_all_values() -> None:
    assert set(LABELS_ZH) == ALL_ENUM_VALUES
    assert all(LABELS_ZH[value].strip() for value in ALL_ENUM_VALUES)


def test_json_serialization_uses_english_values() -> None:
    payload = {"level": StressLevel.HEAVY, "conclusion": SafetyConclusion.REFUSED}
    text = json.dumps(payload, ensure_ascii=False)
    assert '"heavy"' in text
    assert '"refused"' in text
    assert "重度" not in text