from __future__ import annotations

from domain.models.enums import DegradeReason, Phenology, SafetyConclusion, Toxicity
from domain.rules.types import (
    ProductRef,
    SafetyCandidate,
    SafetyIntervalInput,
    SafetyIntervalResult,
)

REASON_INTERVAL_EXCEEDS = "INTERVAL_EXCEEDS_REMAINING"
REASON_NO_ELIGIBLE = "NO_ELIGIBLE_ITEM"
REASON_REUSE = "REUSE_WITHIN_INTERVAL"
REASON_SEASON_LIMIT = "SEASON_LIMIT_REACHED"
LOW_RISK_PHENOLOGY = frozenset({Phenology.SEEDLING, Phenology.BOLL_OPENING})


def _conflict(inp: SafetyIntervalInput) -> ProductRef:
    if inp.conflict_product is not None:
        return inp.conflict_product
    return ProductRef(registry_item_no="UNKNOWN", ai_name="", formulation="")


def _alternatives(inp: SafetyIntervalInput) -> tuple[SafetyCandidate, ...]:
    eligible = [
        candidate
        for candidate in inp.candidates
        if candidate.valid
        and candidate.safety_interval_days <= inp.remaining_days
        and candidate.toxicity == Toxicity.LOW
        and not candidate.season_usage_exceeded
    ]
    return tuple(
        sorted(eligible, key=lambda item: (item.safety_interval_days, item.registry_item_no))
    )


def _format_alternatives(alternatives: tuple[SafetyCandidate, ...]) -> str:
    if not alternatives:
        return "无可选替代"
    return "、".join(
        f"{item.ai_name}{item.formulation}(安全间隔{item.safety_interval_days}天)"
        for item in alternatives
    )


def evaluate_safety_interval(inp: SafetyIntervalInput) -> SafetyIntervalResult:
    remaining = inp.remaining_days
    interval = inp.safety_interval_days
    buffer_days = remaining - interval
    alternatives = _alternatives(inp)
    alternative_text = _format_alternatives(alternatives)

    if inp.candidates and not alternatives:
        min_interval = min(item.safety_interval_days for item in inp.candidates)
        conflict = _conflict(inp)
        message = (
            f"距预计采收 {remaining} 天，安全间隔期 {min_interval} 天，"
            f"冲突药剂 {conflict.product_name}，可选替代 {alternative_text}"
        )
        return SafetyIntervalResult(
            conclusion=SafetyConclusion.REFUSED.value,
            remaining_days=remaining,
            safety_interval_days=interval,
            buffer_days=buffer_days,
            conflict_product=conflict,
            degrade_reasons=(),
            alternatives=alternatives,
            requires_expert_confirm=False,
            reason_code=REASON_NO_ELIGIBLE,
            message=message,
        )

    if remaining < interval:
        conflict = _conflict(inp)
        message = (
            f"距预计采收 {remaining} 天，安全间隔期 {interval} 天，"
            f"冲突药剂 {conflict.product_name}，可选替代 {alternative_text}"
        )
        return SafetyIntervalResult(
            conclusion=SafetyConclusion.REFUSED.value,
            remaining_days=remaining,
            safety_interval_days=interval,
            buffer_days=buffer_days,
            conflict_product=conflict,
            degrade_reasons=(),
            alternatives=alternatives,
            requires_expert_confirm=False,
            reason_code=REASON_INTERVAL_EXCEEDS,
            message=message,
        )

    if inp.same_ai_used_within_interval or inp.season_usage_exceeded:
        reason_code = REASON_REUSE if inp.same_ai_used_within_interval else REASON_SEASON_LIMIT
        conflict = _conflict(inp)
        message = (
            f"距预计采收 {remaining} 天，安全间隔期 {interval} 天，"
            f"冲突药剂 {conflict.product_name}，可选替代 {alternative_text}"
        )
        return SafetyIntervalResult(
            conclusion=SafetyConclusion.REFUSED.value,
            remaining_days=remaining,
            safety_interval_days=interval,
            buffer_days=buffer_days,
            conflict_product=conflict,
            degrade_reasons=(),
            alternatives=alternatives,
            requires_expert_confirm=False,
            reason_code=reason_code,
            message=message,
        )

    reasons: list[DegradeReason] = []
    if 0 <= buffer_days < 3:
        reasons.append(DegradeReason.BUFFER_LT_3)
    if (
        inp.days_since_last_same_ai is not None
        and inp.rotation_interval_days is not None
        and inp.days_since_last_same_ai < inp.rotation_interval_days
    ):
        reasons.append(DegradeReason.ROTATION_INTERVAL)
    if inp.pre_harvest_sensitive:
        reasons.append(DegradeReason.PRE_HARVEST_SENSITIVE)
    if inp.phenology in LOW_RISK_PHENOLOGY:
        reasons.append(DegradeReason.PHENOLOGY_LOW_RISK)

    if reasons:
        reason_text = "、".join(reason.value for reason in reasons)
        message = (
            f"距预计采收 {remaining} 天，安全间隔期 {interval} 天，"
            f"降级原因 {reason_text}，可选替代 {alternative_text}"
        )
        return SafetyIntervalResult(
            conclusion=SafetyConclusion.DEGRADED.value,
            remaining_days=remaining,
            safety_interval_days=interval,
            buffer_days=buffer_days,
            conflict_product=None,
            degrade_reasons=tuple(reasons),
            alternatives=alternatives,
            requires_expert_confirm=True,
            reason_code=None,
            message=message,
        )

    message = (
        f"距预计采收 {remaining} 天，安全间隔期 {interval} 天，"
        f"缓冲 {buffer_days} 天，可选替代 {alternative_text}"
    )
    return SafetyIntervalResult(
        conclusion=SafetyConclusion.SATISFIED.value,
        remaining_days=remaining,
        safety_interval_days=interval,
        buffer_days=buffer_days,
        conflict_product=None,
        degrade_reasons=(),
        alternatives=alternatives,
        requires_expert_confirm=False,
        reason_code=None,
        message=message,
    )