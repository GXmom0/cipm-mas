from __future__ import annotations

from agents.decision.agent import DecisionAgent
from domain.models.enums import StressType, Toxicity
from domain.models.registry import RegistryItem


def _item(no: str, pest: str) -> RegistryItem:
    return RegistryItem(
        registry_item_no=no,
        registry_version="V",
        ai_name=f"药剂{no}",
        formulation="乳油",
        target=StressType.PEST_DISEASE,
        safety_interval_days=7,
        dose_range_ml_per_mu=(1.0, 2.0),
        spray_volume_range_l_per_mu=(1.0, 2.0),
        toxicity=Toxicity.LOW,
        target_pest=pest,
    )


def test_filter_keeps_matching_and_unlabeled() -> None:
    candidates = (_item("A", "棉蚜"), _item("B", "棉铃虫"), _item("C", ""))
    filtered = DecisionAgent._filter_candidates(candidates, "棉蚜")
    assert [item.registry_item_no for item in filtered] == ["A", "C"]


def test_filter_without_target_returns_all() -> None:
    candidates = (_item("A", "棉蚜"), _item("B", "棉铃虫"))
    assert DecisionAgent._filter_candidates(candidates, "") == candidates