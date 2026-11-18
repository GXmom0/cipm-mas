from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from domain.models.enums import AssessmentVerdict
from sdk.contracts.common import SCHEMA_VERSION_LITERAL, StrictModel


class BeforeRef(StrictModel):
    resultNo: str = Field(min_length=1)
    resultVersion: int = Field(ge=1)


class AfterRef(StrictModel):
    sortieNo: str = Field(min_length=1)
    resultNo: str = Field(min_length=1)
    resultVersion: int = Field(ge=1)


class Timeliness(StrictModel):
    completedAt: str
    assessedAt: str
    hoursElapsed: float = Field(ge=0)


class PrescriptionEvidence(StrictModel):
    prescriptionNo: str = Field(min_length=1)
    prescriptionVersion: int = Field(ge=1)
    registryVersion: str = Field(min_length=1)
    zoneCount: int = Field(ge=1)
    productCategories: list[dict[str, str]] = Field(min_length=1)


class Metrics(StrictModel):
    coveragePct: float = Field(ge=0, le=100, description="作业覆盖率")
    suppressionRate: float = Field(ge=-1, le=1, description="胁迫缓解率")
    severeDeviationZones: list[str] = Field(default_factory=list, description="重度偏差分区")
    deviationZones: list[str] = Field(default_factory=list, description="一般偏差分区")


class VerdictRule(StrictModel):
    verdict: AssessmentVerdict
    ruleVersion: str = Field(min_length=1)
    ruleExpression: str = Field(min_length=1)


class NextRound(StrictModel):
    recommendedAction: Literal["continue", "recheck", "manual_expert", "stop"]
    suggestedDate: str | None = None
    note: str = ""


class AssessmentPayload(StrictModel):
    schemaVersion: SCHEMA_VERSION_LITERAL = Field(default="1.0")
    assessmentNo: str = Field(min_length=1)
    workOrderNo: str = Field(min_length=1)
    beforeRef: BeforeRef
    afterRef: AfterRef
    timeliness: Timeliness
    prescriptionEvidence: PrescriptionEvidence
    metrics: Metrics
    verdictRule: VerdictRule
    nextRound: NextRound

    @model_validator(mode="after")
    def _verdict_consistency(self) -> "AssessmentPayload":
        if self.verdictRule.verdict == AssessmentVerdict.QUALIFIED:
            if self.metrics.suppressionRate < 0.6:
                raise ValueError("达标要求缓解率 ≥ 0.6")
            if self.metrics.coveragePct < 95:
                raise ValueError("达标要求覆盖率 ≥ 95")
            if self.metrics.severeDeviationZones:
                raise ValueError("存在重度偏差分区时不得判定达标")
        return self