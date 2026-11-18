from __future__ import annotations

from dataclasses import dataclass

DEFAULT_VOLUME_TOLERANCE = 0.01


@dataclass(frozen=True)
class PrescriptionTriplet:
    ai_name: str
    formulation: str
    dose_ml_per_mu: float
    spray_volume_l_per_mu: float | None = None
    dilution_ratio: float | None = None

    @property
    def category_key(self) -> tuple[str, str]:
        return (self.ai_name, self.formulation)

    def is_complete(self) -> bool:
        if not self.ai_name or not self.formulation:
            return False
        if self.dose_ml_per_mu <= 0:
            return False
        return (self.spray_volume_l_per_mu or 0) > 0 or (self.dilution_ratio or 0) > 0

    def dilution_deviation(self) -> float | None:
        if not self.spray_volume_l_per_mu or not self.dilution_ratio:
            return None
        calculated = self.spray_volume_l_per_mu * 1000 / self.dose_ml_per_mu
        return abs(calculated - self.dilution_ratio) / self.dilution_ratio

    def dilution_consistent(self, tolerance: float = DEFAULT_VOLUME_TOLERANCE) -> bool:
        deviation = self.dilution_deviation()
        return deviation is None or deviation <= tolerance