from __future__ import annotations

from dataclasses import dataclass

from domain.models.enums import IrrigationType, Phenology, Region


@dataclass(frozen=True)
class PlotProfile:
    plot_no: str
    farm_no: str
    area_mu: float
    region: Region
    irrigation: IrrigationType
    phenology: Phenology
    variety: str
    expected_harvest_date: str
    owner: str = ""
    calendar_version: str = "CAL-2026.11"

    @property
    def is_drip(self) -> bool:
        return self.irrigation == IrrigationType.DRIP

    @property
    def is_south(self) -> bool:
        return self.region == Region.SOUTH