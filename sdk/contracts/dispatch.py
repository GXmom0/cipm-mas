from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from sdk.contracts.common import SCHEMA_VERSION_LITERAL, StrictModel


class FlightConstraint(StrictModel):
    altitudeM: float = Field(gt=0, le=30, description="作业飞行高度（米）")
    speedMps: float = Field(gt=0, le=10, description="作业飞行速度（米/秒）")


class Schedule(StrictModel):
    start: str = Field(description="作业开始时间，带 +08:00")
    end: str = Field(description="作业结束时间，带 +08:00")


class WindowCheckRef(StrictModel):
    checkNo: str = Field(pattern=r"^WC-E-[0-9A-Za-z\-]+$", description="执行阶段校验编号")
    verdict: Literal["pass", "pass_with_mandatory_notice", "fail"]
    thresholdVersion: str
    parentCheckNo: str = Field(pattern=r"^WC-D-[0-9A-Za-z\-]+$", description="关联的决策阶段校验编号")


class MandatoryNoticeItem(StrictModel):
    code: str
    measures: list[str] = Field(min_length=1)
    ackRequired: bool = True


class MandatoryAck(StrictModel):
    checked: bool = Field(default=False, description="强制提示是否已确认")
    checkedBy: str | None = None
    checkedAt: str | None = None


class OperatorConfirm(StrictModel):
    confirmedBy: str = Field(min_length=1)
    confirmedAt: str = Field(min_length=1)


class DispatchZone(StrictModel):
    zoneNo: str = Field(min_length=1)
    zeroApplication: bool = False
    doseMlPerMu: float = Field(ge=0)
    sprayVolumeLPerMu: float | None = Field(default=None, ge=0)
    dilutionRatio: float | None = Field(default=None, ge=0)
    productCategory: dict[str, str] | None = None

    @model_validator(mode="after")
    def _triplet(self) -> "DispatchZone":
        if self.zeroApplication:
            return self
        if self.productCategory is None:
            raise ValueError(f"{self.zoneNo} 非零施药必须给出 productCategory")
        if self.doseMlPerMu <= 0:
            raise ValueError(f"{self.zoneNo} 制剂亩用量必须大于 0")
        if not (self.sprayVolumeLPerMu or 0) and not (self.dilutionRatio or 0):
            raise ValueError(f"{self.zoneNo} 喷液量与稀释浓度至少一项")
        return self


class DispatchCommand(StrictModel):
    schemaVersion: SCHEMA_VERSION_LITERAL = Field(default="1.0")
    templateVersion: str = Field(min_length=1, description="指令模板版本，单地块与批量共用")
    workOrderNo: str = Field(min_length=1)
    idempotencyKey: str = Field(default="", description="幂等键，缺省取 workOrderNo")
    plotNo: str = Field(min_length=1)
    prescriptionNo: str = Field(min_length=1)
    prescriptionVersion: int = Field(ge=1)
    batchNo: str | None = Field(default=None, description="批量批次编号")
    queueRank: int | None = Field(default=None, ge=1, description="批次内位次")
    urgency: float | None = Field(default=None, ge=0, description="紧迫度")
    zones: list[DispatchZone] = Field(min_length=1)
    flightConstraint: FlightConstraint
    schedule: Schedule
    windowCheckRef: WindowCheckRef
    mandatoryNotices: list[MandatoryNoticeItem] = Field(default_factory=list)
    mandatoryAck: MandatoryAck = Field(default_factory=MandatoryAck)
    operatorConfirm: OperatorConfirm

    @model_validator(mode="after")
    def _batch_consistency(self) -> "DispatchCommand":
        batch_fields = (self.batchNo, self.queueRank, self.urgency)
        if any(value is not None for value in batch_fields) and not all(
            value is not None for value in batch_fields
        ):
            raise ValueError("batchNo / queueRank / urgency 必须同时给出或同时为空")
        if not self.idempotencyKey:
            object.__setattr__(self, "idempotencyKey", self.workOrderNo)
        if self.mandatoryNotices and not self.mandatoryAck.checked:
            raise ValueError("存在强制提示时必须先确认 mandatoryAck.checked=true")
        if self.windowCheckRef.verdict == "fail":
            raise ValueError("作业窗口校验不通过时禁止下发")
        return self


class DispatchReceipt(StrictModel):
    schemaVersion: SCHEMA_VERSION_LITERAL = Field(default="1.0")
    receiptNo: str = Field(min_length=1)
    workOrderNo: str = Field(min_length=1)
    deviceNo: str = Field(min_length=1)
    accepted: bool
    acceptedAt: str
    message: str = "已受理"


class WorkOrderFeedback(StrictModel):
    schemaVersion: SCHEMA_VERSION_LITERAL = Field(default="1.0")
    workOrderNo: str = Field(min_length=1)
    deviceNo: str = Field(min_length=1)
    actualAreaMu: float = Field(ge=0)
    coveragePct: float = Field(ge=0, le=100)
    avgFlowLPerMu: float = Field(ge=0)
    trackRef: str | None = None
    alarms: list[str] = Field(default_factory=list)
    startedAt: str
    completedAt: str
    status: Literal["completed", "aborted"]