from __future__ import annotations

from dataclasses import dataclass

UNBLOCKED = "unblocked"

STRESS_BLOCKED = "STRESS_BLOCKED"
STRESS_NOT_FROZEN = "STRESS_NOT_FROZEN"
NO_IRRIGATION = "NO_IRRIGATION"
NO_CALENDAR = "NO_CALENDAR"
NO_REGISTRY = "NO_REGISTRY"
NO_WEATHER = "NO_WEATHER"


@dataclass(frozen=True)
class PrerequisiteInput:
    block_status: str = UNBLOCKED
    stress_result_version: int | None = 1
    has_irrigation: bool = True
    has_calendar: bool = True
    has_registry_snapshot: bool = True
    has_weather: bool = True


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    blocked: bool
    missing_items: tuple[str, ...]
    reason_codes: tuple[str, ...]
    message: str


def check_prerequisites(inp: PrerequisiteInput) -> GuardResult:
    # spec 5.3.1-1：必须以已冻结且不阻断的胁迫结果、含灌溉的档案、含采收日期的日历、72h 气象、
    # 可用登记目录为输入；任一缺失即阻止处方生成。
    missing: list[str] = []
    codes: list[str] = []

    if inp.block_status != UNBLOCKED:
        missing.append(f"胁迫识别结果处于阻断/未决状态（{inp.block_status}）")
        codes.append(STRESS_BLOCKED)
    if inp.stress_result_version is None:
        missing.append("胁迫识别结果未冻结（无版本号）")
        codes.append(STRESS_NOT_FROZEN)
    if not inp.has_irrigation:
        missing.append("种植档案缺少灌溉方式")
        codes.append(NO_IRRIGATION)
    if not inp.has_calendar:
        missing.append("农事日历缺少采收日期")
        codes.append(NO_CALENDAR)
    if not inp.has_registry_snapshot:
        missing.append("登记用药目录快照不可用")
        codes.append(NO_REGISTRY)
    if not inp.has_weather:
        missing.append("72 小时气象数据缺失")
        codes.append(NO_WEATHER)

    if missing:
        return GuardResult(
            allowed=False,
            blocked=True,
            missing_items=tuple(missing),
            reason_codes=tuple(codes),
            message="处方生成前置门禁未通过：" + "；".join(missing),
        )
    return GuardResult(
        allowed=True,
        blocked=False,
        missing_items=(),
        reason_codes=(),
        message="处方生成前置门禁通过",
    )