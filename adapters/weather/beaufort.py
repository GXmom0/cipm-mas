from __future__ import annotations

_THRESHOLDS: tuple[tuple[float, int], ...] = (
    (0.3, 0),
    (1.6, 1),
    (3.4, 2),
    (5.5, 3),
    (8.0, 4),
    (10.8, 5),
    (13.9, 6),
    (17.2, 7),
    (20.8, 8),
    (24.5, 9),
    (28.5, 10),
    (32.7, 11),
)


def beaufort_level(wind_speed_ms: float) -> int:
    speed = max(0.0, float(wind_speed_ms))
    for upper, grade in _THRESHOLDS:
        if speed < upper:
            return grade
    return 12