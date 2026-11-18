from __future__ import annotations

from domain.rules.types import CompoundComponent, CompoundGuardResult, RuleInputError


def check_single_agent(components: tuple[CompoundComponent, ...]) -> CompoundGuardResult:
    if not components:
        raise RuleInputError("复配组分列表不得为空")
    for component in components:
        if not component.ai_name or not component.formulation:
            raise RuleInputError("复配组分的有效成分与剂型不得为空")

    unique: dict[tuple[str, str], CompoundComponent] = {}
    for component in components:
        unique.setdefault(component.category_key, component)

    count = len(unique)
    max_interval = max(component.safety_interval_days for component in unique.values())

    if count >= 2:
        labels = "、".join(component.category_label for component in unique.values())
        message = (
            f"检测到 {count} 个药剂品类（{labels}），V1.0 不支持复配自动生成，"
            f"已转农技专家人工复核；安全间隔期按组合最长值 {max_interval} 天由专家手工执行。"
        )
        return CompoundGuardResult(
            detected=True,
            allowed=False,
            action="intercepted_to_expert",
            category_count=count,
            max_safety_interval_days=max_interval,
            applies_to="expert_manual_only",
            requires_expert_review=True,
            auto_dispatch_allowed=False,
            message=message,
        )

    only = next(iter(unique.values()))
    if only.formulation_type == "mixture_registered":
        message = (
            f"登记混剂 {only.category_label} 按单一品类使用，允许自动生成处方；"
            f"处方中保留 formulation_type=mixture_registered 并展示有效成分。"
        )
        return CompoundGuardResult(
            detected=False,
            allowed=True,
            action="none",
            category_count=1,
            max_safety_interval_days=only.safety_interval_days,
            applies_to="auto_allowed",
            requires_expert_review=False,
            auto_dispatch_allowed=True,
            message=message,
        )

    message = (
        f"检测到 1 个药剂品类（{only.category_label}），符合 V1.0 单剂处方要求，"
        f"安全间隔期 {only.safety_interval_days} 天。"
    )
    return CompoundGuardResult(
        detected=False,
        allowed=True,
        action="none",
        category_count=1,
        max_safety_interval_days=only.safety_interval_days,
        applies_to="auto_allowed",
        requires_expert_review=False,
        auto_dispatch_allowed=True,
        message=message,
    )