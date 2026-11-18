from __future__ import annotations

from dataclasses import dataclass

MIN_TEMPERATURE_C = 12.5
MIN_AVG_TEMPERATURE_C = 23.0
MAX_WIND_LEVEL = 3
SOUTH_AFTERNOON_RH_THRESHOLD = 30.0
PRECIPITATION_PROBABILITY_LIMIT = 30.0
PRECIPITATION_HORIZON_HOURS = 6

CONCLUSION_PASS = "pass"
CONCLUSION_PASS_WITH_NOTICE = "pass_with_mandatory_notice"
CONCLUSION_FAIL = "fail"
FAIL_MESSAGE = "作业窗口校验不通过，转待重新排期"


@dataclass(frozen=True)
class PrecipitationCheckInput:
    probabilities_pct: tuple[float, ...]
    data_available: bool = True


@dataclass(frozen=True)
class PrecipitationCheckResult:
    conclusion: str
    passed: bool
    exceed_hours: tuple[int, ...]
    probabilities_pct: tuple[float, ...]
    violations: tuple[str, ...]
    message: str


def check_precipitation_probability(inp: PrecipitationCheckInput) -> PrecipitationCheckResult:
    # spec 5.3.1-13 / 5.9：未来 6 小时逐时降水概率不得 > 30%，数据缺失按不通过处理。
    probabilities = tuple(inp.probabilities_pct)
    if not inp.data_available or len(probabilities) < PRECIPITATION_HORIZON_HOURS:
        return PrecipitationCheckResult(
            conclusion=CONCLUSION_FAIL,
            passed=False,
            exceed_hours=(),
            probabilities_pct=probabilities,
            violations=("降水概率数据缺失或不足 6 小时，按不通过处理",),
            message=FAIL_MESSAGE,
        )
    exceed = tuple(
        hour
        for hour, value in enumerate(probabilities, start=1)
        if value > PRECIPITATION_PROBABILITY_LIMIT
    )
    if exceed:
        violations = tuple(
            f"第 {hour} 小时降水概率 {probabilities[hour - 1]}% 超过 {PRECIPITATION_PROBABILITY_LIMIT}%"
            for hour in exceed
        )
        return PrecipitationCheckResult(
            conclusion=CONCLUSION_FAIL,
            passed=False,
            exceed_hours=exceed,
            probabilities_pct=probabilities,
            violations=violations,
            message=FAIL_MESSAGE,
        )
    return PrecipitationCheckResult(
        conclusion=CONCLUSION_PASS,
        passed=True,
        exceed_hours=(),
        probabilities_pct=probabilities,
        violations=(),
        message="降水概率校验通过",
    )


@dataclass(frozen=True)
class WorkWindowInput:
    min_temperatures: tuple[float, ...]
    avg_temperatures: tuple[float, ...]
    wind_levels: tuple[int, ...]
    region: str = "south"
    afternoon_humidity_pct: float | None = None
    data_available: bool = True
    precipitation_probabilities_pct: tuple[float, ...] | None = None


@dataclass(frozen=True)
class WorkWindowResult:
    conclusion: str
    passed: bool
    violations: tuple[str, ...]
    notices: tuple[str, ...]
    message: str
    min_temperature: float | None = None
    min_avg_temperature: float | None = None
    max_wind_level: int | None = None


def evaluate_work_window(inp: WorkWindowInput) -> WorkWindowResult:
    if not inp.data_available:
        return WorkWindowResult(
            conclusion=CONCLUSION_FAIL,
            passed=False,
            violations=("作业窗口数据不可用，按不通过处理",),
            notices=(),
            message=FAIL_MESSAGE,
        )

    violations: list[str] = []
    if inp.precipitation_probabilities_pct is not None:
        precipitation = check_precipitation_probability(
            PrecipitationCheckInput(probabilities_pct=inp.precipitation_probabilities_pct)
        )
        violations.extend(precipitation.violations)
    for index, value in enumerate(inp.min_temperatures, start=1):
        if value < MIN_TEMPERATURE_C:
            violations.append(f"第 {index} 日最低气温 {value}℃ 低于 {MIN_TEMPERATURE_C}℃ 红线")
    for index, value in enumerate(inp.avg_temperatures, start=1):
        if value <= MIN_AVG_TEMPERATURE_C:
            violations.append(f"第 {index} 日日均温 {value}℃ 未高于 {MIN_AVG_TEMPERATURE_C}℃")
    for index, value in enumerate(inp.wind_levels, start=1):
        if value > MAX_WIND_LEVEL:
            violations.append(f"第 {index} 小时风速 {value} 级超过 {MAX_WIND_LEVEL} 级")

    min_temperature = min(inp.min_temperatures) if inp.min_temperatures else None
    min_avg_temperature = min(inp.avg_temperatures) if inp.avg_temperatures else None
    max_wind_level = max(inp.wind_levels) if inp.wind_levels else None

    if violations:
        return WorkWindowResult(
            conclusion=CONCLUSION_FAIL,
            passed=False,
            violations=tuple(violations),
            notices=(),
            message=FAIL_MESSAGE,
            min_temperature=min_temperature,
            min_avg_temperature=min_avg_temperature,
            max_wind_level=max_wind_level,
        )

    notices: tuple[str, ...] = ()
    conclusion = CONCLUSION_PASS
    if (
        inp.region == "south"
        and inp.afternoon_humidity_pct is not None
        and inp.afternoon_humidity_pct < SOUTH_AFTERNOON_RH_THRESHOLD
    ):
        conclusion = CONCLUSION_PASS_WITH_NOTICE
        notices = (
            f"南疆午后相对湿度 {inp.afternoon_humidity_pct}% 低于 {SOUTH_AFTERNOON_RH_THRESHOLD}%，须执行防漂移措施",
        )

    message = "作业窗口校验通过" if conclusion == CONCLUSION_PASS else "作业窗口校验通过（带强制提示）"
    return WorkWindowResult(
        conclusion=conclusion,
        passed=True,
        violations=(),
        notices=notices,
        message=message,
        min_temperature=min_temperature,
        min_avg_temperature=min_avg_temperature,
        max_wind_level=max_wind_level,
    )