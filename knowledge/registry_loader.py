from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

REAL_REGISTRY_PATH = Path(__file__).resolve().parent / "real_registry.json"
REAL_REGISTRY_VERSION = "REG-REAL-2026.11"


def default_mode() -> str:
    return (os.environ.get("CIPM_REGISTRY_SOURCE") or "mock").strip().lower()


def _to_stub_dict(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "registryItemNo": item["registry_item_no"],
        "registryVersion": item.get("registry_version", REAL_REGISTRY_VERSION),
        "category": {"aiName": item["ai_name"], "formulation": item["formulation"]},
        "registrationNo": item["registration_no"],
        "concentration": item.get("concentration", ""),
        "toxicity": item["toxicity"],
        "target": item["target"],
        "targetPest": item.get("target_pest", ""),
        "crop": item.get("crop", "cotton"),
        "safetyIntervalDays": item["safety_interval_days"],
        "doseRangeMlPerMu": list(item["dose_range_ml_per_mu"]),
        "doseUnit": item.get("dose_unit", "ml/mu"),
        "doseNote": item.get("dose_note", ""),
        "sprayVolumeRangeLPerMu": list(item["spray_volume_range_l_per_mu"]),
        "applicationMethod": item.get("application_method", "ground_spray"),
        "uavSprayConversion": item.get("uav_spray_conversion", "待接入规范"),
        "seasonUsageLimit": item.get("season_usage_limit", 3),
        "valid": item.get("valid", True),
        "formulationType": item.get("formulation_type", "single"),
        "source": item.get("source", ""),
    }


def load_real_registry() -> list[dict[str, Any]]:
    if not REAL_REGISTRY_PATH.exists():
        return []
    raw = json.loads(REAL_REGISTRY_PATH.read_text(encoding="utf-8"))
    records = raw if isinstance(raw, list) else raw.get("items", [])
    return [_to_stub_dict(item) for item in records]


def load_registry(mode: str | None = None) -> list[dict[str, Any]]:
    resolved = (mode or default_mode()).lower()
    if resolved == "real":
        return load_real_registry()
    from mock.builder import REGISTRY_ITEMS

    return copy.deepcopy(REGISTRY_ITEMS)