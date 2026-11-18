from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.enums import DegradeReason, Phenology, Toxicity

RULE_VERSION = "SAFETY-RULE-1.0"
SINGLE_AGENT_RULE_VERSION = "SINGLE-AGENT-RULE-1.0"


class RuleInputError(ValueError):
    def __init__(self, message: str, error_code: str = "CIPM-RULE-5005") -> None:
        self.error_code = error_code
        super().__init__(message)


@dataclass(frozen=True)
class ProductRef:
    registry_item_no: str
    ai_name: str
    formulation: str

    @property
    def product_name(self) -> str:
        if not self.ai_name:
            return "未指定药剂"
        if not self.formulation:
            return self.ai_name
        return f"{self.ai_name}·{self.formulation}"


@dataclass(frozen=True)
class SafetyCandidate:
    registry_item_no: str
    ai_name: str
    formulation: str
    safety_interval_days: int
    dose_range_ml_per_mu: tuple[float, float] = (0.0, 0.0)
    toxicity: Toxicity = Toxicity.LOW
    season_usage_exceeded: bool = False
    valid: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.safety_interval_days <= 30:
            raise RuleInputError(
                f"候选目录项 {self.registry_item_no} 的安全间隔期必须在 1—30 天之间"
            )


@dataclass(frozen=True)
class SafetyIntervalInput:
    remaining_days: int
    safety_interval_days: int
    candidates: tuple[SafetyCandidate, ...] = ()
    phenology: Phenology = Phenology.FLOWER_BOLL
    same_ai_used_within_interval: bool = False
    season_usage_exceeded: bool = False
    days_since_last_same_ai: int | None = None
    rotation_interval_days: int | None = None
    pre_harvest_sensitive: bool = False
    conflict_product: ProductRef | None = None

    def __post_init__(self) -> None:
        if self.remaining_days < 0:
            raise RuleInputError("remaining_days 不得为负数")
        if not 1 <= self.safety_interval_days <= 30:
            raise RuleInputError("safety_interval_days 必须在 1—30 天之间")
        if self.days_since_last_same_ai is not None and self.days_since_last_same_ai < 0:
            raise RuleInputError("days_since_last_same_ai 不得为负数")
        if self.rotation_interval_days is not None and self.rotation_interval_days < 0:
            raise RuleInputError("rotation_interval_days 不得为负数")


@dataclass(frozen=True)
class SafetyIntervalResult:
    conclusion: str
    remaining_days: int
    safety_interval_days: int
    buffer_days: int
    conflict_product: ProductRef | None
    degrade_reasons: tuple[DegradeReason, ...]
    alternatives: tuple[SafetyCandidate, ...]
    requires_expert_confirm: bool
    reason_code: str | None
    message: str
    rule_version: str = RULE_VERSION


@dataclass(frozen=True)
class CompoundComponent:
    ai_name: str
    formulation: str
    registry_item_no: str
    safety_interval_days: int
    formulation_type: str = "single"

    def __post_init__(self) -> None:
        if not self.ai_name or not self.formulation:
            raise RuleInputError("复配组分必须同时给出有效成分与剂型")
        if not 1 <= self.safety_interval_days <= 30:
            raise RuleInputError(
                f"组分 {self.registry_item_no} 的安全间隔期必须在 1—30 天之间"
            )

    @property
    def category_key(self) -> tuple[str, str]:
        return (self.ai_name, self.formulation)

    @property
    def category_label(self) -> str:
        return f"{self.ai_name}·{self.formulation}"


@dataclass(frozen=True)
class CompoundGuardResult:
    detected: bool
    allowed: bool
    action: str
    category_count: int
    max_safety_interval_days: int | None
    applies_to: str
    requires_expert_review: bool
    auto_dispatch_allowed: bool
    message: str
    rule_version: str = SINGLE_AGENT_RULE_VERSION