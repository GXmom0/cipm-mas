from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.enums import BlockStatus, ReviewStatus, StressLevel, StressType


@dataclass(frozen=True)
class ExplainabilityEvidence:
    ndvi_deviation: float | None = None
    ndvi_baseline_id: str | None = None
    ndvi_baseline_version: str | None = None
    ndvi_method: str = "分区均值与同物候期健康基线差值"
    pest_density: float | None = None
    pest_density_unit: str = "头/百株"
    pest_density_basis: str | None = None

    def has_any(self) -> bool:
        return self.ndvi_deviation is not None or self.pest_density is not None

    @property
    def available_indicators(self) -> tuple[str, ...]:
        names = []
        if self.ndvi_deviation is not None:
            names.append("ndviDeviation")
        if self.pest_density is not None:
            names.append("pestDensity")
        return tuple(names)


@dataclass(frozen=True)
class StressPartition:
    partition_no: str
    area_mu: float
    stress_type: StressType
    stress_level: StressLevel
    confidence: float
    explainability: ExplainabilityEvidence
    threshold_entry_id: str
    threshold_version: str
    review_status: ReviewStatus = ReviewStatus.NONE_REQUIRED
    geometry_ref: str = ""
    frozen: bool = False

    def requires_review(self) -> bool:
        return self.confidence < 0.7 or not self.explainability.has_any()


@dataclass(frozen=True)
class StressResult:
    task_no: str
    result_no: str
    result_version: int
    partitions: tuple[StressPartition, ...] = field(default_factory=tuple)
    block_status: BlockStatus = BlockStatus.UNBLOCKED
    duration_sec: float = 0.0

    @property
    def blocking_partitions(self) -> tuple[str, ...]:
        return tuple(p.partition_no for p in self.partitions if p.requires_review())

    @property
    def decision_allowed(self) -> bool:
        return self.block_status == BlockStatus.UNBLOCKED or self.block_status == BlockStatus.RELEASED