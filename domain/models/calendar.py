from __future__ import annotations

from dataclasses import dataclass

from domain.models.enums import Phenology


@dataclass(frozen=True)
class CalendarEntry:
    plot_no: str
    phenology: Phenology
    expected_harvest_date: str
    window_close_in_days: int
    version: str = "CAL-2026.11"

    def is_window_closed(self) -> bool:
        return self.window_close_in_days < 0