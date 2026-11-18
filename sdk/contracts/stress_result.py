from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from domain.models.enums import BlockStatus, DataIntegrity, ReviewStatus, StressLevel, StressType
from sdk.contracts.common import SCHEMA_VERSION_LITERAL, StrictModel


class NdviDeviation(StrictModel):
    value: float = Field(description="分区 NDVI 均值与同物候期健康基线的差值")
    baselineId: str = Field(description="健康基线编号")
    baselineVersion: str = Field(description="健康基线版本")
    method: str = Field(description="计算方法说明")


class PestDensity(StrictModel):
    value: float = Field(ge=0, description="虫口密度推算值")
    unit: Literal["头/百株"] = Field(description="固定单位：头/百株")
    basis: str = Field(description="推算依据")


class Explainability(StrictModel):
    ndviDeviation: NdviDeviation | None = Field(default=None, description="NDVI 偏离证据")
    pestDensity: PestDensity | None = Field(default=None, description="虫口密度证据")

    @model_validator(mode="after")
    def _at_least_one_indicator(self) -> "Explainability":
        if self.ndviDeviation is None and self.pestDensity is None:
            raise ValueError("explainability 至少需要 ndviDeviation 或 pestDensity 之一")
        return self


class ThresholdRef(StrictModel):
    entryId: str = Field(description="防治阈值条目编号")
    version: str = Field(description="阈值版本")


class ReviewInfo(StrictModel):
    status: ReviewStatus = Field(description="复核状态")
    reviewer: str | None = Field(default=None, description="复核人")
    reviewedAt: str | None = Field(default=None, description="复核时间，ISO8601 带 +08:00")
    beforeLevel: StressLevel | None = Field(default=None, description="改判前等级")
    afterLevel: StressLevel | None = Field(default=None, description="改判后等级")
    conclusion: str | None = Field(default=None, description="复核结论说明")


class PartitionResult(StrictModel):
    partitionNo: str = Field(min_length=1, description="分区编号")
    areaMu: float = Field(gt=0, description="分区面积（亩）")
    geometryRef: str = Field(description="分区几何快照 OBS 引用")
    stressType: StressType = Field(description="胁迫类型")
    stressLevel: StressLevel = Field(description="胁迫等级，四档")
    targetPest: str = Field(default="", description="目标害虫具体名称，如棉蚜；空表示未识别到具体害虫")
    confidence: float = Field(ge=0, le=1, description="识别置信度")
    explainability: Explainability = Field(description="可解释指标，至少一项")
    thresholdRef: ThresholdRef = Field(description="阈值引用")
    review: ReviewInfo = Field(description="复核状态")
    frozen: bool = Field(default=False, description="被处方引用后必须为 true")

    @model_validator(mode="after")
    def _review_consistency(self) -> "PartitionResult":
        if self.confidence < 0.7 and self.review.status != ReviewStatus.PENDING:
            raise ValueError("confidence < 0.7 时 review.status 必须为 pending")
        if self.stressType == StressType.UNDETERMINED and self.review.status == ReviewStatus.NONE_REQUIRED:
            raise ValueError("stressType=undetermined 时不得标记无需复核")
        return self


class OrthophotoMeta(StrictModel):
    sortieNo: str = Field(min_length=1, description="架次编号")
    readyTime: str = Field(description="正射影像产品就绪时刻，带 +08:00")
    bands: list[str] = Field(min_length=2, description="波段清单")
    gsdCm: float = Field(gt=0, le=5, description="地面分辨率（厘米）")
    cloudPct: float = Field(ge=0, le=100, description="云量百分比")
    coverRatio: float = Field(gt=0, le=1, description="地块覆盖率")
    productVersion: str = Field(min_length=1, description="影像平台产品版本")

    @model_validator(mode="after")
    def _bands_required(self) -> "OrthophotoMeta":
        normalized = {band.upper() for band in self.bands}
        missing = {"NIR", "RED"} - normalized
        if missing:
            raise ValueError(f"bands 缺少必需波段：{sorted(missing)}")
        if not self.readyTime.endswith("+08:00"):
            raise ValueError("readyTime 必须使用 +08:00 时区")
        return self


class TaskBlock(StrictModel):
    status: BlockStatus = Field(description="任务阻断状态")
    blockingPartitions: list[str] = Field(default_factory=list, description="触发阻断的分区编号")
    reasonCodes: list[str] = Field(default_factory=list, description="阻断原因码")


class RecognitionMeta(StrictModel):
    durationSec: float = Field(gt=0, le=600, description="识别耗时，从正射影像就绪起算，≤600 秒")
    dataIntegrity: DataIntegrity = Field(description="数据完整性")
    degraded: dict[str, str] | None = Field(default=None, description="降级标识")


class EvidenceItem(StrictModel):
    type: str = Field(description="证据类型，如 threshold / baseline")
    refId: str = Field(description="证据编号")
    version: str = Field(description="证据版本")


class StressResultPayload(StrictModel):
    schemaVersion: SCHEMA_VERSION_LITERAL = Field(default="1.0", description="契约版本")
    taskNo: str = Field(min_length=1, description="巡田任务编号")
    resultNo: str = Field(min_length=1, description="识别结果编号")
    resultVersion: int = Field(ge=1, description="结果版本，递增不可回退")
    orthophoto: OrthophotoMeta = Field(description="正射影像产品元数据")
    taskBlock: TaskBlock = Field(description="任务阻断信息")
    partitions: list[PartitionResult] = Field(min_length=1, description="分区识别结果")
    recognitionMeta: RecognitionMeta = Field(description="识别元数据")
    evidence: list[EvidenceItem] = Field(min_length=1, description="可回放证据，至少一条")

    @model_validator(mode="after")
    def _block_consistency(self) -> "StressResultPayload":
        block = self.taskBlock
        if block.status == BlockStatus.BLOCKED_PENDING_REVIEW:
            if not block.blockingPartitions:
                raise ValueError("blocked_pending_review 时 blockingPartitions 不得为空")
            known = {partition.partitionNo: partition for partition in self.partitions}
            unknown = [no for no in block.blockingPartitions if no not in known]
            if unknown:
                raise ValueError(f"blockingPartitions 引用了不存在的分区：{unknown}")
            for no in block.blockingPartitions:
                if known[no].review.status == ReviewStatus.NONE_REQUIRED:
                    raise ValueError(f"被阻断分区 {no} 的复核状态不得为 none_required")
        if block.status != BlockStatus.BLOCKED_PENDING_REVIEW and block.blockingPartitions:
            raise ValueError("仅阻断状态可填写 blockingPartitions")
        return self