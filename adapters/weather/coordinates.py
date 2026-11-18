from __future__ import annotations

PLOT_COORDINATES: dict[str, tuple[float, float]] = {
    "PLOT-0912": (41.16, 80.28),
    "PLOT-0913": (40.55, 81.27),
    "PLOT-0914": (41.76, 86.14),
    "PLOT-0915": (41.17, 80.31),
    "PLOT-0916": (41.20, 80.35),
}

DEFAULT_COORDINATES: tuple[float, float] = (41.16, 80.28)


def coordinates_for(plot_no: str) -> tuple[float, float]:
    return PLOT_COORDINATES.get(plot_no, DEFAULT_COORDINATES)