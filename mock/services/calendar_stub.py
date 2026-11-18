from __future__ import annotations

from typing import Any

from mock.scenarios import ALL_SCENARIOS


def get(plot_no: str) -> dict[str, Any]:
    for spec in ALL_SCENARIOS:
        for plot in spec.plots:
            if plot.plot_no == plot_no:
                return {
                    "plotNo": plot.plot_no,
                    "phenology": plot.phenology.value,
                    "expectedHarvestDate": plot.harvest_date,
                    "remainingDays": plot.remaining_days,
                    "windowCloseInDays": max(1, plot.remaining_days // 3),
                    "version": "CAL-2026.11",
                }
    raise KeyError(f"农事日历不存在：{plot_no}")