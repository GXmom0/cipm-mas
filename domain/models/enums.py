from __future__ import annotations

from enum import Enum


class StressType(str, Enum):
    PEST_DISEASE = "pest_disease"
    NUTRIENT_DEFICIENCY = "nutrient_deficiency"
    DROUGHT = "drought"
    WATERLOGGING = "waterlogging"
    UNDETERMINED = "undetermined"


class StressLevel(str, Enum):
    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class ReviewStatus(str, Enum):
    NONE_REQUIRED = "none_required"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    OVERRIDDEN = "overridden"
    UNDETERMINED = "undetermined"


class ReviewConclusion(str, Enum):
    CONFIRM = "confirm"
    OVERRIDE = "override"
    UNDETERMINED = "undetermined"


class BlockStatus(str, Enum):
    UNBLOCKED = "unblocked"
    BLOCKED_PENDING_REVIEW = "blocked_pending_review"
    RELEASED = "released"


class SafetyConclusion(str, Enum):
    SATISFIED = "satisfied"
    DEGRADED = "degraded"
    REFUSED = "refused"


class DegradeReason(str, Enum):
    BUFFER_LT_3 = "BUFFER_LT_3"
    ROTATION_INTERVAL = "ROTATION_INTERVAL"
    PRE_HARVEST_SENSITIVE = "PRE_HARVEST_SENSITIVE"
    PHENOLOGY_LOW_RISK = "PHENOLOGY_LOW_RISK"


class PrescriptionStatus(str, Enum):
    DRAFT = "draft"
    PENDING_WINDOW = "pending_window"
    DEGRADED_PENDING_CONFIRM = "degraded_pending_confirm"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUSED = "refused"


class WorkOrderStatus(str, Enum):
    PENDING_SCHEDULE = "pending_schedule"
    PENDING_DISPATCH = "pending_dispatch"
    DISPATCHED = "dispatched"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ABORTED = "aborted"
    RESCHEDULED = "rescheduled"


class BatchState(str, Enum):
    DRAFT = "draft"
    PENDING_CONFIRM = "pending_confirm"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AssessmentVerdict(str, Enum):
    QUALIFIED = "qualified"
    NOT_QUALIFIED = "not_qualified"
    PENDING = "pending"


class CompoundAction(str, Enum):
    NONE = "none"
    INTERCEPTED_TO_EXPERT = "intercepted_to_expert"


class Toxicity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Phenology(str, Enum):
    SEEDLING = "seedling"
    BUD = "bud"
    FLOWER_BOLL = "flower_boll"
    BOLL_OPENING = "boll_opening"


class IrrigationType(str, Enum):
    DRIP = "drip"
    NON_DRIP = "non_drip"


class Region(str, Enum):
    SOUTH = "south"
    NORTH = "north"


class DataIntegrity(str, Enum):
    COMPLETE = "complete"
    PARTIAL_MISSING = "partial_missing"
    UNAVAILABLE = "unavailable"


class BadgeCode(str, Enum):
    BLOCKED = "BLOCKED"
    DEGRADED = "DEGRADED"
    REFUSED = "REFUSED"
    RESCHEDULED = "RESCHEDULED"


LABELS_ZH: dict[str, str] = {
    StressType.PEST_DISEASE.value: "病虫害",
    StressType.NUTRIENT_DEFICIENCY.value: "缺素",
    StressType.DROUGHT.value: "干旱",
    StressType.WATERLOGGING.value: "渍害",
    StressType.UNDETERMINED.value: "待定",
    StressLevel.NONE.value: "无",
    StressLevel.LIGHT.value: "轻度",
    StressLevel.MEDIUM.value: "中度",
    StressLevel.HEAVY.value: "重度",
    ReviewStatus.NONE_REQUIRED.value: "无需复核",
    ReviewStatus.PENDING.value: "待复核",
    ReviewStatus.CONFIRMED.value: "已复核-确认",
    ReviewStatus.OVERRIDDEN.value: "已复核-改判",
    ReviewStatus.UNDETERMINED.value: "已复核-无法判定",
    ReviewConclusion.CONFIRM.value: "确认",
    ReviewConclusion.OVERRIDE.value: "改判",
    ReviewConclusion.UNDETERMINED.value: "无法判定",
    BlockStatus.UNBLOCKED.value: "未阻断",
    BlockStatus.BLOCKED_PENDING_REVIEW.value: "阻断待复核",
    BlockStatus.RELEASED.value: "已解除",
    SafetyConclusion.SATISFIED.value: "满足",
    SafetyConclusion.DEGRADED.value: "降级",
    SafetyConclusion.REFUSED.value: "拒绝",
    DegradeReason.BUFFER_LT_3.value: "缓冲不足3天",
    DegradeReason.ROTATION_INTERVAL.value: "轮换间隔不足",
    DegradeReason.PRE_HARVEST_SENSITIVE.value: "采收前敏感窗口",
    DegradeReason.PHENOLOGY_LOW_RISK.value: "苗期或吐絮期",
    PrescriptionStatus.DRAFT.value: "草稿",
    PrescriptionStatus.PENDING_WINDOW.value: "待作业窗口",
    PrescriptionStatus.DEGRADED_PENDING_CONFIRM.value: "降级待确认",
    PrescriptionStatus.PENDING_REVIEW.value: "待审核",
    PrescriptionStatus.APPROVED.value: "已通过",
    PrescriptionStatus.REJECTED.value: "已驳回",
    PrescriptionStatus.REFUSED.value: "已拒绝",
    WorkOrderStatus.PENDING_SCHEDULE.value: "待排期",
    WorkOrderStatus.PENDING_DISPATCH.value: "待下发",
    WorkOrderStatus.DISPATCHED.value: "已下发",
    WorkOrderStatus.EXECUTING.value: "执行中",
    WorkOrderStatus.COMPLETED.value: "已完成",
    WorkOrderStatus.ABORTED.value: "已中止",
    WorkOrderStatus.RESCHEDULED.value: "待重新排期",
    BatchState.DRAFT.value: "草稿",
    BatchState.PENDING_CONFIRM.value: "待确认",
    BatchState.QUEUED.value: "已入队",
    BatchState.EXECUTING.value: "执行中",
    BatchState.COMPLETED.value: "已完成",
    BatchState.CANCELLED.value: "已取消",
    AssessmentVerdict.QUALIFIED.value: "达标",
    AssessmentVerdict.NOT_QUALIFIED.value: "未达标",
    AssessmentVerdict.PENDING.value: "待评估",
    CompoundAction.NONE.value: "无需处理",
    CompoundAction.INTERCEPTED_TO_EXPERT.value: "已转专家复核",
    Toxicity.LOW.value: "低毒",
    Toxicity.MEDIUM.value: "中等毒",
    Toxicity.HIGH.value: "高毒",
    Phenology.SEEDLING.value: "苗期",
    Phenology.BUD.value: "蕾期",
    Phenology.FLOWER_BOLL.value: "花铃期",
    Phenology.BOLL_OPENING.value: "吐絮期",
    IrrigationType.DRIP.value: "滴灌",
    IrrigationType.NON_DRIP.value: "非滴灌",
    Region.SOUTH.value: "南疆",
    Region.NORTH.value: "北疆",
    DataIntegrity.COMPLETE.value: "完整",
    DataIntegrity.PARTIAL_MISSING.value: "部分缺失",
    DataIntegrity.UNAVAILABLE.value: "不可用",
    BadgeCode.BLOCKED.value: "阻断待复核",
    BadgeCode.DEGRADED.value: "降级待确认",
    BadgeCode.REFUSED.value: "已拒绝",
    BadgeCode.RESCHEDULED.value: "待重新排期",
}

ALL_ENUM_VALUES: set[str] = {
    member.value
    for enum_cls in (
        StressType,
        StressLevel,
        ReviewStatus,
        ReviewConclusion,
        BlockStatus,
        SafetyConclusion,
        DegradeReason,
        PrescriptionStatus,
        WorkOrderStatus,
        BatchState,
        AssessmentVerdict,
        CompoundAction,
        Toxicity,
        Phenology,
        IrrigationType,
        Region,
        DataIntegrity,
        BadgeCode,
    )
    for member in enum_cls
}


def label_of(value: str) -> str:
    return LABELS_ZH.get(value, value)