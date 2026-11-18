from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.models.enums import Phenology, StressLevel, Toxicity
from domain.models.registry import RegistryItem
from domain.rules import (
    CompoundComponent,
    SafetyCandidate,
    SafetyIntervalInput,
    check_single_agent,
    evaluate_safety_interval,
)

VOLUME_TOLERANCE = 0.01


@dataclass(frozen=True)
class LlmZoneSuggestion:
    zone_no: str
    ai_name: str
    formulation: str
    dose_ml_per_mu: float
    spray_volume_l_per_mu: float | None = None
    dilution_ratio: float | None = None
    registry_item_no: str = ""
    safety_interval_days: int | None = None
    zero_application: bool = False


@dataclass(frozen=True)
class DecisionContext:
    task_no: str
    plot_no: str
    remaining_days: int
    phenology: Phenology
    candidates: tuple[RegistryItem, ...]
    drip: bool = True
    device_max_spray_l_per_mu: float = 2.0
    target_pest: str = ""
    same_ai_used_within_interval: bool = False
    season_usage_exceeded: bool = False
    pre_harvest_sensitive: bool = False
    days_since_last_same_ai: int | None = None
    rotation_interval_days: int | None = None


@dataclass(frozen=True)
class SandboxViolation:
    code: str
    message: str
    zone_no: str | None = None


@dataclass(frozen=True)
class SandboxResult:
    allowed: bool
    status: str
    zones: tuple[LlmZoneSuggestion, ...]
    violations: tuple[SandboxViolation, ...] = ()
    safety_conclusion: str | None = None
    remaining_days: int = 0
    safety_interval_days: int = 0
    buffer_days: int = 0
    degrade_reasons: tuple[str, ...] = ()
    requires_expert_confirm: bool = False
    compound_detected: bool = False
    max_safety_interval_days: int | None = None
    audit_event_id: str | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class PrescriptionSafetySandbox:
    def __init__(self, audit_repo: Any | None = None) -> None:
        self._audit = audit_repo

    def validate(
        self,
        zones: tuple[LlmZoneSuggestion, ...],
        context: DecisionContext,
        llm_raw: Any = None,
        agent_run_id: str | None = None,
        trace_id: str | None = None,
    ) -> SandboxResult:
        violations: list[SandboxViolation] = []
        active = tuple(zone for zone in zones if not zone.zero_application)
        if not active:
            violations.append(SandboxViolation("EMPTY_SUGGESTION", "LLM 未给出任何非零施药分区"))

        matched: list[RegistryItem] = []
        for zone in active:
            item = self._match_registry(zone, context.candidates)
            if item is None:
                violations.append(
                    SandboxViolation(
                        "REGISTRY_ITEM_MISSING",
                        f"分区 {zone.zone_no} 的药剂未绑定新疆现行登记用药目录项",
                        zone.zone_no,
                    )
                )
                continue
            matched.append(item)
            violations.extend(self._check_triplet(zone, item, context))

        compound = self._check_single_agent(matched)
        compound_detected = bool(compound is not None and compound.detected)
        if compound_detected:
            violations.append(
                SandboxViolation(
                    "COMPOUND_INTERCEPTED",
                    compound.message,
                )
            )

        safety = self._check_safety_interval(matched, context)
        if safety is not None and safety.conclusion == "refused":
            violations.append(
                SandboxViolation(
                    "SAFETY_INTERVAL_REFUSED",
                    safety.message,
                )
            )

        allowed = not violations
        if allowed and safety is not None and safety.conclusion == "degraded":
            status = "degraded_pending_confirm"
        elif allowed:
            status = "pending_review"
        else:
            status = "refused"

        message = "LLM 建议通过本地规则沙箱校验。" if allowed else self._reject_message(violations, safety)
        result = SandboxResult(
            allowed=allowed,
            status=status,
            zones=zones,
            violations=tuple(violations),
            safety_conclusion=None if safety is None else safety.conclusion,
            remaining_days=context.remaining_days,
            safety_interval_days=0 if safety is None else safety.safety_interval_days,
            buffer_days=0 if safety is None else safety.buffer_days,
            degrade_reasons=() if safety is None else tuple(reason.value for reason in safety.degrade_reasons),
            requires_expert_confirm=False if safety is None else safety.requires_expert_confirm,
            compound_detected=compound_detected,
            max_safety_interval_days=None if compound is None else compound.max_safety_interval_days,
            message=message,
            details={
                "rulesVersion": "SAFETY-RULE-1.0",
                "singleAgentRuleVersion": "SINGLE-AGENT-RULE-1.0",
                "candidateCount": len(context.candidates),
            },
        )
        if not allowed:
            result = self._write_llm_error(result, context, llm_raw, agent_run_id, trace_id)
        return result

    def _match_registry(
        self, zone: LlmZoneSuggestion, candidates: tuple[RegistryItem, ...]
    ) -> RegistryItem | None:
        for item in candidates:
            if zone.registry_item_no and item.registry_item_no == zone.registry_item_no:
                if item.ai_name == zone.ai_name and item.formulation == zone.formulation:
                    return item
        for item in candidates:
            if item.ai_name == zone.ai_name and item.formulation == zone.formulation:
                return item
        return None

    def _check_triplet(
        self, zone: LlmZoneSuggestion, item: RegistryItem, context: DecisionContext
    ) -> list[SandboxViolation]:
        issues: list[SandboxViolation] = []
        dose = zone.dose_ml_per_mu
        spray = zone.spray_volume_l_per_mu or 0.0
        dilution = zone.dilution_ratio or 0.0

        if not zone.ai_name or not zone.formulation:
            issues.append(SandboxViolation("TRIPLET_INCOMPLETE", f"分区 {zone.zone_no} 缺少药剂品类", zone.zone_no))
        if dose <= 0:
            issues.append(SandboxViolation("TRIPLET_INCOMPLETE", f"分区 {zone.zone_no} 制剂亩用量必须大于 0", zone.zone_no))
        if spray <= 0 and dilution <= 0:
            issues.append(
                SandboxViolation(
                    "TRIPLET_INCOMPLETE",
                    f"分区 {zone.zone_no} 缺少喷液量或稀释浓度",
                    zone.zone_no,
                )
            )

        low, high = item.dose_range_ml_per_mu
        if dose > 0 and not (low <= dose <= high):
            issues.append(
                SandboxViolation(
                    "DOSE_OUT_OF_REGISTRY_RANGE",
                    f"分区 {zone.zone_no} 制剂亩用量 {dose} 超出登记区间 [{low}, {high}]",
                    zone.zone_no,
                )
            )

        if spray > 0 and dilution > 0 and dose > 0:
            calculated = spray * 1000 / dose
            deviation = abs(calculated - dilution) / dilution
            if deviation > VOLUME_TOLERANCE:
                issues.append(
                    SandboxViolation(
                        "VOLUME_INCONSISTENT",
                        f"分区 {zone.zone_no} 喷液量与稀释浓度换算偏差 {deviation:.2%} 超过 1%",
                        zone.zone_no,
                    )
                )

        # 登记兑水量（spray_volume_range_l_per_mu）作为地面喷雾参考展示字段；
        # 无人机低容量喷雾的喷液量与地面兑水量语义不同（换算规范待接入），
        # 设备能力单独按 device_max_spray_l_per_mu 校验处方实际喷液量。
        if spray > 0 and spray > context.device_max_spray_l_per_mu:
            issues.append(
                SandboxViolation(
                    "DEVICE_MAX_EXCEEDED",
                    f"分区 {zone.zone_no} 处方喷液量 {spray} 超过设备上限 {context.device_max_spray_l_per_mu}",
                    zone.zone_no,
                )
            )
        return issues

    def _check_single_agent(self, matched: list[RegistryItem]) -> Any:
        components = []
        seen: set[tuple[str, str]] = set()
        for item in matched:
            key = (item.ai_name, item.formulation)
            if key in seen:
                continue
            seen.add(key)
            components.append(
                CompoundComponent(
                    ai_name=item.ai_name,
                    formulation=item.formulation,
                    registry_item_no=item.registry_item_no,
                    safety_interval_days=item.safety_interval_days,
                    formulation_type=item.formulation_type,
                )
            )
        if not components:
            return None
        return check_single_agent(tuple(components))

    def _check_safety_interval(
        self,
        matched: list[RegistryItem],
        context: DecisionContext,
    ) -> Any:
        if not matched:
            return None
        intervals = {item.safety_interval_days for item in matched}
        effective = max(intervals)
        candidates = tuple(
            SafetyCandidate(
                registry_item_no=item.registry_item_no,
                ai_name=item.ai_name,
                formulation=item.formulation,
                safety_interval_days=item.safety_interval_days,
                dose_range_ml_per_mu=item.dose_range_ml_per_mu,
                toxicity=item.toxicity,
            )
            for item in context.candidates
            if item.valid and item.crop == "cotton"
        )
        first_item = matched[0]
        from domain.rules import ProductRef

        return evaluate_safety_interval(
            SafetyIntervalInput(
                remaining_days=context.remaining_days,
                safety_interval_days=effective,
                candidates=candidates,
                phenology=context.phenology,
                same_ai_used_within_interval=context.same_ai_used_within_interval,
                season_usage_exceeded=context.season_usage_exceeded,
                days_since_last_same_ai=context.days_since_last_same_ai,
                rotation_interval_days=context.rotation_interval_days,
                pre_harvest_sensitive=context.pre_harvest_sensitive,
                conflict_product=ProductRef(
                    registry_item_no=first_item.registry_item_no,
                    ai_name=first_item.ai_name,
                    formulation=first_item.formulation,
                ),
            )
        )

    def _reject_message(self, violations: list[SandboxViolation], safety: Any) -> str:
        head = "LLM 处方建议被安全沙箱拦截"
        if safety is not None and safety.conclusion == "refused":
            return f"{head}：{safety.message}"
        return f"{head}：{'；'.join(item.message for item in violations)}"

    def _write_llm_error(
        self,
        result: SandboxResult,
        context: DecisionContext,
        llm_raw: Any,
        agent_run_id: str | None,
        trace_id: str | None,
    ) -> SandboxResult:
        if self._audit is None:
            return result
        try:
            audit_id = self._audit.append(
                event_type="LLM_ERROR",
                operator="decision_safety_sandbox",
                biz_id=context.task_no,
                before={"llmSuggestion": llm_raw},
                after={
                    "violations": [
                        {"code": item.code, "message": item.message, "zoneNo": item.zone_no}
                        for item in result.violations
                    ],
                    "safetyConclusion": result.safety_conclusion,
                    "remainingDays": result.remaining_days,
                    "safetyIntervalDays": result.safety_interval_days,
                    "bufferDays": result.buffer_days,
                },
                result="rejected",
                trace_id=trace_id,
                agent_run_id=agent_run_id,
            )
        except Exception:
            return result
        return SandboxResult(
            allowed=result.allowed,
            status=result.status,
            zones=result.zones,
            violations=result.violations,
            safety_conclusion=result.safety_conclusion,
            remaining_days=result.remaining_days,
            safety_interval_days=result.safety_interval_days,
            buffer_days=result.buffer_days,
            degrade_reasons=result.degrade_reasons,
            requires_expert_confirm=result.requires_expert_confirm,
            compound_detected=result.compound_detected,
            max_safety_interval_days=result.max_safety_interval_days,
            audit_event_id=audit_id,
            message=result.message,
            details=result.details,
        )