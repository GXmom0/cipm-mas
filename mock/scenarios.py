from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.enums import (
    BadgeCode,
    IrrigationType,
    Phenology,
    PrescriptionStatus,
    Region,
    SafetyConclusion,
    StressType,
)
from mock.seed import date_after, iso_after


@dataclass(frozen=True)
class PlotSpec:
    plot_no: str
    plot_name: str
    area_mu: float
    region: Region
    irrigation: IrrigationType
    phenology: Phenology
    remaining_days: int
    safety_interval_days: int
    partition_count: int
    stressed_partitions: int
    stress_type: StressType = StressType.PEST_DISEASE
    expected_conclusion: str = SafetyConclusion.SATISFIED.value
    expected_status: str = PrescriptionStatus.PENDING_REVIEW.value
    expected_badges: tuple[BadgeCode, ...] = ()
    low_confidence_partition: str | None = None
    low_confidence_value: float = 0.62

    @property
    def harvest_date(self) -> str:
        return date_after(self.remaining_days + 1)

    @property
    def deadline_date(self) -> str:
        return date_after(1)



@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    scenario_name: str
    file_name: str
    plots: tuple[PlotSpec, ...]
    description: str
    expected_badges: tuple[BadgeCode, ...] = field(default_factory=tuple)

    @property
    def entry_plot_no(self) -> str:
        return self.plots[0].plot_no


NORMAL_PLOT = PlotSpec(
    plot_no="PLOT-0912",
    plot_name="呼图壁示范田-东区",
    area_mu=120.0,
    region=Region.SOUTH,
    irrigation=IrrigationType.DRIP,
    phenology=Phenology.FLOWER_BOLL,
    remaining_days=20,
    safety_interval_days=7,
    partition_count=12,
    stressed_partitions=6,
)

DEGRADED_PLOT = PlotSpec(
    plot_no="PLOT-0915",
    plot_name="呼图壁示范田-西区",
    area_mu=80.0,
    region=Region.SOUTH,
    irrigation=IrrigationType.DRIP,
    phenology=Phenology.FLOWER_BOLL,
    remaining_days=9,
    safety_interval_days=7,
    partition_count=9,
    stressed_partitions=5,
    expected_conclusion=SafetyConclusion.DEGRADED.value,
    expected_status=PrescriptionStatus.DEGRADED_PENDING_CONFIRM.value,
    expected_badges=(BadgeCode.DEGRADED,),
)

LOW_CONFIDENCE_PLOT = PlotSpec(
    plot_no="PLOT-0913",
    plot_name="石河子示范田-北区",
    area_mu=96.0,
    region=Region.NORTH,
    irrigation=IrrigationType.NON_DRIP,
    phenology=Phenology.BUD,
    remaining_days=25,
    safety_interval_days=10,
    partition_count=10,
    stressed_partitions=4,
    stress_type=StressType.UNDETERMINED,
    low_confidence_partition="Z03",
    expected_badges=(BadgeCode.BLOCKED,),
)

SAFETY_CONFLICT_PLOT = PlotSpec(
    plot_no="PLOT-0914",
    plot_name="阿克苏示范田-南支",
    area_mu=64.0,
    region=Region.SOUTH,
    irrigation=IrrigationType.DRIP,
    phenology=Phenology.FLOWER_BOLL,
    remaining_days=5,
    safety_interval_days=7,
    partition_count=8,
    stressed_partitions=1,
    expected_conclusion=SafetyConclusion.REFUSED.value,
    expected_status=PrescriptionStatus.REFUSED.value,
    expected_badges=(BadgeCode.REFUSED,),
    low_confidence_partition=None,
)

RESCHEDULED_PLOT = PlotSpec(
    plot_no="PLOT-0916",
    plot_name="阿克苏示范田-北支",
    area_mu=72.0,
    region=Region.SOUTH,
    irrigation=IrrigationType.DRIP,
    phenology=Phenology.BOLL_OPENING,
    remaining_days=30,
    safety_interval_days=7,
    partition_count=6,
    stressed_partitions=3,
    expected_status=PrescriptionStatus.APPROVED.value,
    expected_badges=(BadgeCode.RESCHEDULED,),
)

NORMAL = ScenarioSpec(
    scenario_id="normal_plot",
    scenario_name="正常地块与缓冲不足地块",
    file_name="normal_plot.json",
    plots=(NORMAL_PLOT, DEGRADED_PLOT),
    description="演示满足与降级两种安全间隔结论，处方可正常进入审核。",
    expected_badges=(BadgeCode.DEGRADED,),
)

LOW_CONFIDENCE = ScenarioSpec(
    scenario_id="low_confidence_plot",
    scenario_name="置信度不足地块",
    file_name="low_confidence_plot.json",
    plots=(LOW_CONFIDENCE_PLOT,),
    description="Z03 置信度 0.62，任务级整体阻断，不生成任何处方。",
    expected_badges=(BadgeCode.BLOCKED,),
)

SAFETY_CONFLICT = ScenarioSpec(
    scenario_id="safety_conflict_plot",
    scenario_name="安全间隔冲突与作业窗口重排地块",
    file_name="safety_conflict_plot.json",
    plots=(SAFETY_CONFLICT_PLOT, RESCHEDULED_PLOT),
    description="R=5、S=7 触发拒绝；另一地块因执行前窗口温度不通过进入待重新排期。",
    expected_badges=(BadgeCode.REFUSED, BadgeCode.RESCHEDULED),
)

ALL_SCENARIOS: tuple[ScenarioSpec, ...] = (NORMAL, LOW_CONFIDENCE, SAFETY_CONFLICT)
SCENARIO_BY_ID = {spec.scenario_id: spec for spec in ALL_SCENARIOS}

EXPECTED_VALUES = {
    "PLOT-0912": {
        "remainingDays": 20,
        "safetyIntervalDays": 7,
        "bufferDays": 13,
        "conclusion": "satisfied",
        "degradeReasons": [],
    },
    "PLOT-0915": {
        "remainingDays": 9,
        "safetyIntervalDays": 7,
        "bufferDays": 2,
        "conclusion": "degraded",
        "degradeReasons": ["BUFFER_LT_3"],
    },
    "PLOT-0913": {
        "taskBlockStatus": "blocked_pending_review",
        "blockingPartitions": ["Z03"],
        "confidence": 0.62,
        "prescriptions": 0,
    },
    "PLOT-0914": {
        "remainingDays": 5,
        "safetyIntervalDays": 7,
        "bufferDays": -2,
        "conclusion": "refused",
        "conflictProduct": "啶虫脒·乳油",
    },
    "PLOT-0916": {
        "prescriptionStatus": "approved",
        "workOrderStatus": "rescheduled",
        "windowVerdict": "fail",
    },
}

SNAPSHOT_AT = iso_after(minutes=5)