from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from agents.execution.agent import ExecutionAgent
from apps.platform_api.core.clock import iso_now
from apps.platform_api.core.deps import get_audit_repo, get_clock, get_idempotency_repo
from apps.platform_api.core.errors import BizError
from apps.platform_api.core.trace import trace_id_of
from apps.platform_api.repository.audit_repo import AuditRepo
from apps.platform_api.repository.idempotency_repo import (
    CANCEL_ALREADY_ACKED,
    CANCEL_ALREADY_CANCELLED,
    CANCEL_AMBIGUOUS,
    CANCEL_CANCELLED,
    CANCEL_NOT_CANCELLABLE,
    CANCEL_NOT_FOUND,
    STATUS_ACKED,
    IdempotencyRepo,
)
from mock.loader import plot_bundle
from sdk.contracts.common import StrictModel
from sdk.contracts.envelope import Envelope
from sdk.contracts.error_codes import ErrorCode

router = APIRouter(tags=["execution"])


class ExecutionDispatchRequest(StrictModel):
    plotNo: str = Field(min_length=1)
    idempotencyKey: str = Field(default="", description="幂等键；也可用 HTTP 头 Idempotency-Key，二者取其一")
    operator: str = Field(default="manager_li")


class ExecutionCancelRequest(StrictModel):
    workOrderNo: str = Field(default="", description="工单号；与 idempotencyKey 至少给一个")
    idempotencyKey: str = Field(default="", description="幂等键；与 workOrderNo 至少给一个")
    reason: str = Field(default="", description="取消原因")
    operator: str = Field(default="manager_li", description="取消操作人，写入审计")



def _envelope(request: Request, data: dict[str, Any], clock: Any, biz_id: str | None) -> JSONResponse:
    envelope = Envelope[dict](
        traceId=trace_id_of(request),
        bizId=biz_id,
        data=data,
        timestamp=iso_now(clock),
    )
    return JSONResponse(content=envelope.model_dump(mode="json"))


@router.post("/agents/execution/dispatch")
def dispatch(
    payload: ExecutionDispatchRequest,
    request: Request,
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
    idempotency_repo: IdempotencyRepo = Depends(get_idempotency_repo),
    audit_repo: AuditRepo = Depends(get_audit_repo),
    clock=Depends(get_clock),
) -> JSONResponse:
    key = (idempotency_key_header or payload.idempotencyKey or "").strip()
    if not key:
        raise BizError(ErrorCode.IDEMPOTENCY_KEY_REQUIRED, http_status=400)

    try:
        bundle = plot_bundle(payload.plotNo)
    except KeyError:
        raise BizError(
            ErrorCode.EXEC_PRECONDITION_FAILED,
            message=f"未找到地块 {payload.plotNo} 的演示数据。",
            http_status=404,
        )

    claim = idempotency_repo.claim(key, {"plotNo": payload.plotNo})

    if not claim.claimed:
        record = claim.record
        if record.status == STATUS_ACKED:
            data = dict(record.result or {})
            data["replayed"] = True
            audit_repo.append(
                "workorder.dispatch",
                payload.operator,
                biz_id=record.workOrderNo,
                after={
                    "status": data.get("status", STATUS_ACKED),
                    "workOrderNo": record.workOrderNo,
                    "idempotencyKey": key,
                    "replayed": True,
                },
            )
            return _envelope(request, data, clock, record.workOrderNo)
        raise BizError(
            ErrorCode.EXEC_PRECONDITION_FAILED,
            message="相同幂等键的作业正在下发中，请勿重复提交。",
            http_status=409,
        )

    outcome = ExecutionAgent().dispatch(payload.plotNo, bundle.get("prescription"), operator=payload.operator)
    result: dict[str, Any] = {
        "workOrderNo": outcome.work_order_no,
        "plotNo": outcome.plot_no,
        "status": outcome.status,
        "message": outcome.message,
        "command": outcome.command,
        "receipt": outcome.receipt,
        "violations": list(outcome.violations),
        "notices": list(outcome.notices),
        "replayed": False,
    }
    if outcome.dispatched:
        idempotency_repo.mark_acked(key, outcome.work_order_no, result=result)
        audit_repo.append(
            "workorder.dispatch",
            payload.operator,
            biz_id=outcome.work_order_no,
            after={
                "status": outcome.status,
                "workOrderNo": outcome.work_order_no,
                "idempotencyKey": key,
                "replayed": False,
            },
        )
    else:
        idempotency_repo.mark_failed(key, outcome.message, work_order_no=outcome.work_order_no or None, result=result)
        audit_repo.append(
            "workorder.dispatch",
            payload.operator,
            biz_id=outcome.work_order_no or payload.plotNo,
            after={
                "status": outcome.status,
                "workOrderNo": outcome.work_order_no,
                "idempotencyKey": key,
                "reason": outcome.message,
                "replayed": False,
            },
        )
    return _envelope(request, result, clock, outcome.work_order_no)


@router.post("/agents/execution/cancel")
def cancel(
    payload: ExecutionCancelRequest,
    request: Request,
    idempotency_repo: IdempotencyRepo = Depends(get_idempotency_repo),
    audit_repo: AuditRepo = Depends(get_audit_repo),
    clock=Depends(get_clock),
) -> JSONResponse:
    key = (payload.idempotencyKey or "").strip() or None
    work_order_no = (payload.workOrderNo or "").strip() or None
    if not key and not work_order_no:
        raise BizError(
            ErrorCode.EXEC_PRECONDITION_FAILED,
            message="必须提供 workOrderNo 或 idempotencyKey 之一。",
            http_status=400,
        )

    outcome = idempotency_repo.cancel(key=key, work_order_no=work_order_no, reason=payload.reason)
    if outcome.outcome == CANCEL_NOT_FOUND:
        raise BizError(ErrorCode.WORK_ORDER_NOT_FOUND, http_status=404)
    if outcome.outcome == CANCEL_AMBIGUOUS:
        raise BizError(ErrorCode.WORK_ORDER_AMBIGUOUS, http_status=409)
    if outcome.outcome == CANCEL_ALREADY_ACKED:
        raise BizError(ErrorCode.WORK_ORDER_ALREADY_ACKED, http_status=409)
    if outcome.outcome == CANCEL_NOT_CANCELLABLE:
        record = outcome.record
        raise BizError(
            ErrorCode.EXEC_PRECONDITION_FAILED,
            message=f"工单当前状态 {record.status if record else '未知'} 不可取消。",
            http_status=409,
        )

    record = outcome.record
    if outcome.outcome == CANCEL_CANCELLED:
        audit_repo.append(
            "workorder.cancel",
            payload.operator,
            biz_id=record.workOrderNo,
            before={"status": outcome.previous_status},
            after={
                "status": record.status,
                "reason": record.reason,
                "idempotencyKey": record.key,
            },
        )

    data = {
        "workOrderNo": record.workOrderNo,
        "status": record.status,
        "reason": record.reason,
        "replayed": outcome.outcome == CANCEL_ALREADY_CANCELLED,
    }
    return _envelope(request, data, clock, record.workOrderNo)