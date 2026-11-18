from __future__ import annotations

from dataclasses import dataclass

from domain.models.enums import StressType, Toxicity


@dataclass(frozen=True)
class RegistryItem:
    registry_item_no: str
    registry_version: str
    ai_name: str
    formulation: str
    target: StressType
    safety_interval_days: int
    dose_range_ml_per_mu: tuple[float, float]
    spray_volume_range_l_per_mu: tuple[float, float]
    toxicity: Toxicity
    crop: str = "cotton"
    valid: bool = True
    formulation_type: str = "single"
    season_usage_limit: int = 3
    registration_no: str = "PD2026XXXX"
    target_pest: str = ""
    application_method: str = "ground_spray"

    @property
    def category_key(self) -> tuple[str, str]:
        return (self.ai_name, self.formulation)

    @property
    def volume_midpoint(self) -> float:
        low, high = self.spray_volume_range_l_per_mu
        return round((low + high) / 2, 2)

    def eligible_for(self, stress_type: StressType, remaining_days: int) -> bool:
        if not self.valid or self.crop != "cotton":
            return False
        if self.target != stress_type:
            return False
        return self.safety_interval_days <= remaining_days