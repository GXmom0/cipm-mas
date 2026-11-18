from __future__ import annotations

from agents.decision.safety_sandbox import (
    DecisionContext,
    LlmZoneSuggestion,
    PrescriptionSafetySandbox,
)
from domain.models.enums import Phenology, StressType, Toxicity
from domain.models.registry import RegistryItem
from knowledge.registry_loader import load_real_registry


def _real_item(item_no: str) -> RegistryItem:
    raw = next(item for item in load_real_registry() if item["registryItemNo"] == item_no)
    return RegistryItem(
        registry_item_no=raw["registryItemNo"],
        registry_version=raw["registryVersion"],
        ai_name=raw["category"]["aiName"],
        formulation=raw["category"]["formulation"],
        target=StressType(raw["target"]),
        safety_interval_days=raw["safetyIntervalDays"],
        dose_range_ml_per_mu=tuple(raw["doseRangeMlPerMu"]),
        spray_volume_range_l_per_mu=tuple(raw["sprayVolumeRangeLPerMu"]),
        toxicity=Toxicity(raw["toxicity"]),
        formulation_type=raw["formulationType"],
    )


def test_two_independent_registered_items_mixed_intercepted() -> None:
    cypermethrin = _real_item("REAL-01")  # 高效氯氰菊酯 乳油
    etoxazole = _real_item("REAL-03")  # 乙唑螨腈 悬浮剂
    zones = (
        LlmZoneSuggestion(
            zone_no="Z01",
            ai_name="高效氯氰菊酯",
            formulation="乳油",
            dose_ml_per_mu=30.0,
            spray_volume_l_per_mu=1.6,
            registry_item_no="REAL-01",
        ),
        LlmZoneSuggestion(
            zone_no="Z02",
            ai_name="乙唑螨腈",
            formulation="悬浮剂",
            dose_ml_per_mu=8.0,
            spray_volume_l_per_mu=1.6,
            registry_item_no="REAL-03",
        ),
    )
    context = DecisionContext(
        task_no="PT-COMPOUND-DEMO",
        plot_no="PLOT-0912",
        remaining_days=30,
        phenology=Phenology.FLOWER_BOLL,
        candidates=(cypermethrin, etoxazole),
        drip=True,
        device_max_spray_l_per_mu=2.0,
    )

    result = PrescriptionSafetySandbox().validate(zones, context)

    assert result.compound_detected is True
    assert any(v.code == "COMPOUND_INTERCEPTED" for v in result.violations)
    assert result.allowed is False