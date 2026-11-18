from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

TZ_EAST8 = timezone(timedelta(hours=8))


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(TZ_EAST8)


class FixedClock:
    def __init__(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            raise ValueError("FixedClock 必须使用带时区的时间")
        self._moment = moment

    def now(self) -> datetime:
        return self._moment


def iso_now(clock: Clock) -> str:
    return clock.now().astimezone(TZ_EAST8).isoformat()