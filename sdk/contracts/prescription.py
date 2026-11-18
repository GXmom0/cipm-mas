from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from domain.models.enums import CompoundAction, DegradeReason, PrescriptionStatus, SafetyConclusion, Toxicity
from sdk.contracts.common import SCHEMA_VERSION_LITERAL, StrictModel

VOLUME_TOLERANCE = 0.01


class RegistrySnapshot(StrictModel):
    version: str = Field(min_length=1, description="登记用药目录整体版本")
    syncedAt: str = Field(description="目录同步时间，带 +08:00")
    degraded: bool = Field(default=False, description="是否使用降级快照")


class CompoundComponentRef(StrictModel):
    category: dict[str, str] = Field(description="品类 {aiName, formulation}")
    registryItemNo: str = Field(min_length=1, description="目录项编号")


class CompoundGuard(StrictModel):
    detected: bool = Field(description="是否检测到复配")
    components: list[CompoundComponentRef] = Field(default_factory=list, description="检测到的组分")
    action: CompoundAction = Field(description="处置动作")

    @model_validator(mode="after")
    def _intercept_consistency(self) -> "CompoundGuard":
        if self.detected and self.action != CompoundAction.INTERCEPTED_TO_EXPERT:
            raise ValueError("复配检测命中时必须转专家复核")
        if not self.detected and self.action != CompoundAction.NONE:
            raise ValueError("未检测到复配时 action 必须为 none")
        return self


class SafetyAlternative(StrictModel):
    registryItemNo: str = Field(min_length=1)
    category: dict[str, str]
    safetyIntervalDays: int = Field(ge=1, le=30)
    doseRange: list[float] = Field(min_length=2, max_length=2)


class ConflictProduct(StrictModel):
    registryItemNo: str = Field(min_length=1)
    category: dict[str, str]


class SafetyCheck(StrictModel):
    conclusion: SafetyConclusion = Field(description="安全间隔结论")
    remainingDays: int = Field(ge=0, description="采收剩余天数 R")
    safetyIntervalDays: int = Field(ge=1, le=30, description="安全间隔期 S")
    bufferDays: int = Field(description="R − S，可为负")
    conflictProduct: ConflictProduct | None = Field(default=None, description="拒绝时的冲突药剂")
    degradeReasons: list[DegradeReason] = Field(default_factory=list, description="降级原因")
    alternatives: list[SafetyAlternative] = Field(default_factory=list, description="可选替代，拒绝时可供重开处方")

    @model_validator(mode="after")
    def _rule_consistency(self) -> "SafetyCheck":
        if self.bufferDays != self.remainingDays - self.safetyIntervalDays:
            raise ValueError("bufferDays 必须恒等于 remainingDays − safetyIntervalDays")
        if self.conclusion == SafetyConclusion.REFUSED and self.conflictProduct is None:
            raise ValueError("conclusion=refused 时必须给出 conflictProduct")
        if self.conclusion == SafetyConclusion.DEGRADED and not self.degradeReasons:
            raise ValueError("conclusion=degraded 时 degradeReasons 不得为空")
        if self.conclusion == SafetyConclusion.SATISFIED and self.degradeReasons:
            raise ValueError("conclusion=satisfied 时不得携带降级原因")
        return self


class MandatoryNotice(StrictModel):
    code: Literal["DRIFT_GUARD_SOUTH"]
    measures: list[str] = Field(min_length=4, max_length=4, description="防漂移四项措施")
    ackRequired: bool = Field(default=True)


class WindowCheck(StrictModel):
    checkNo: str = Field(pattern=r"^WC-D-[0-9A-Za-z\-]+$", description="决策阶段校验编号")
    conclusion: Literal["pass", "pass_with_mandatory_notice", "fail"]
    thresholdVersion: str = Field(min_length=1)
    parentCheckNo: str | None = Field(default=None)
    mandatoryNotices: list[MandatoryNotice] = Field(default_factory=list)
    candidateWindows: list[dict[str, str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _notice_consistency(self) -> "WindowCheck":
        if self.conclusion == "pass_with_mandatory_notice" and not self.mandatoryNotices:
            raise ValueError("带强制提示通过时必须给出 mandatoryNotices")
        if self.conclusion != "pass_with_mandatory_notice" and self.mandatoryNotices:
            raise ValueError("仅带强制提示通过时可给出 mandatoryNotices")
        return self


class DosageTruncation(StrictModel):
    applied: bool
    reason: Literal["below_min", "above_max"]
    originalValue: float = Field(gt=0)
    finalValue: float = Field(gt=0)


class VolumeCorrection(StrictModel):
    applied: bool
    reason: Literal["drip_midpoint", "device_max"]
    originalValue: float = Field(gt=0)
    finalValue: float = Field(gt=0)


class PrescriptionProduct(StrictModel):
    registryItemNo: str = Field(min_length=1)
    registryVersion: str = Field(min_length=1)
    category: dict[str, str] = Field(description="{aiName, formulation}，V1.0 每分区仅一个品类")
    registrationNo: str = Field(min_length=1, description="新疆现行登记证号")
    toxicity: Toxicity

    @model_validator(mode="after")
    def _category_complete(self) -> "PrescriptionProduct":
        for key in ("aiName", "formulation"):
            if not self.category.get(key):
                raise ValueError(f"category.{key} 不得为空")
        return self


class PrescriptionZone(StrictModel):
    zoneNo: str = Field(min_length=1, description="与识别结果分区编号一致")
    zeroApplication: bool = Field(description="stressLevel=none 时必须为 true")
    product: PrescriptionProduct | None = Field(default=None)
    doseMlPerMu: float = Field(ge=0, description="制剂亩用量，毫升/亩")
    sprayVolumeLPerMu: float | None = Field(default=None, ge=0, description="喷液量，升/亩")
    dilutionRatio: float | None = Field(default=None, ge=0, description="稀释浓度，倍液")
    safetyIntervalDays: int | None = Field(default=None, ge=1, le=30)
    seasonUsageBefore: int = Field(default=0, ge=0)
    doseTruncation: DosageTruncation | None = None
    volumeCorrection: VolumeCorrection | None = None

    @model_validator(mode="after")
    def _triplet(self) -> "PrescriptionZone":
        if self.zeroApplication:
            if self.product is not None:
                raise ValueError(f"{self.zoneNo} 零施药分区不得给出 product")
            if self.doseMlPerMu != 0:
                raise ValueError(f"{self.zoneNo} 零施药分区 doseMlPerMu 必须为 0")
            if self.sprayVolumeLPerMu not in (None, 0):
                raise ValueError(f"{self.zoneNo} 零施药分区 sprayVolumeLPerMu 必须为空或 0")
            if self.safetyIntervalDays is not None:
                raise ValueError(f"{self.zoneNo} 零施药分区 safetyIntervalDays 必须为空")
            return self

        if self.product is None:
            raise ValueError(f"{self.zoneNo} 非零施药分区必须给出 product")
        if self.doseMlPerMu <= 0:
            raise ValueError(f"{self.zoneNo} 制剂亩用量必须大于 0")
        volume = self.sprayVolumeLPerMu or 0
        ratio = self.dilutionRatio or 0
        if volume <= 0 and ratio <= 0:
            raise ValueError(f"{self.zoneNo} 喷液量与稀释浓度至少填写一项")
        if volume > 0 and ratio > 0:
            calculated = volume * 1000 / self.doseMlPerMu
            deviation = abs(calculated - ratio) / ratio
            if deviation > VOLUME_TOLERANCE:
                raise ValueError(
                    f"{self.zoneNo} 喷液量与稀释浓度换算偏差 {deviation:.4f} 超过 1%"
                )
        if self.safetyIntervalDays is None:
            raise ValueError(f"{self.zoneNo} 非零施药分区必须给出 safetyIntervalDays")
        return self


class ReviewEvidence(StrictModel):
    reviewer: str
    reviewedAt: str
    partitionNo: str
    beforeLevel: str
    afterLevel: str
    conclusion: str


class EvidenceRefs(StrictModel):
    thresholdVersion: str
    baselineVersion: str
    kbRefs: list[dict[str, str]] = Field(default_factory=list)
    historyPrescriptionRef: str | None = None


class PrescriptionPayload(StrictModel):
    schemaVersion: SCHEMA_VERSION_LITERAL = Field(default="1.0")
    prescriptionNo: str = Field(min_length=1)
    prescriptionVersion: int = Field(ge=1)
    taskNo: str = Field(min_length=1)
    resultNo: str = Field(min_length=1)
    resultVersion: int = Field(ge=1)
    status: PrescriptionStatus
    registrySnapshot: RegistrySnapshot
    compoundGuard: CompoundGuard
    safetyCheck: SafetyCheck
    windowCheck: WindowCheck
    zones: list[PrescriptionZone] = Field(default_factory=list)
    reviewEvidence: ReviewEvidence | None = None
    evidenceRefs: EvidenceRefs

    @model_validator(mode="after")
    def _payload_consistency(self) -> "PrescriptionPayload":
        if self.compoundGuard.detected:
            if self.zones:
                raise ValueError("compoundGuard.detected=true 时不得生成 zones")
            if self.status != PrescriptionStatus.REFUSED:
                raise ValueError("复配拦截时 status 必须为 refused")
        elif not self.zones:
            raise ValueError("非复配处方至少需要 1 个分区")
        if self.status == PrescriptionStatus.APPROVED:
            if self.windowCheck.conclusion not in ("pass", "pass_with_mandatory_notice"):
                raise ValueError("approved 处方的作业窗口校验结论必须为通过或带强制提示通过")
            if self.registrySnapshot.degraded:
                raise ValueError("使用降级目录快照的处方不得直接置为 approved")
        if self.compoundGuard.detected and self.safetyCheck.conclusion != SafetyConclusion.REFUSED:
            raise ValueError("复配拦截时安全间隔结论必须为 refused")
        return self