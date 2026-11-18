from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from apps.platform_api.core.clock import iso_now
from apps.platform_api.core.deps import get_clock, get_snapshot_repo
from apps.platform_api.core.errors import BizError
from apps.platform_api.core.trace import agent_run_id_of, trace_id_of
from apps.platform_api.repository.snapshot_repo import SnapshotRepo
from sdk.contracts.envelope import Envelope
from sdk.contracts.error_codes import ErrorCode

router = APIRouter(tags=["dashboard"])

VALID_STAGES = {"patrol", "prescription", "execution", "assessment", "all"}


@router.get("/dashboard")
def dashboard(
    request: Request,
    farmNo: str | None = Query(default=None, description="农场编号，缺省返回全部"),
    stage: str | None = Query(default=None, description="阶段过滤：patrol/prescription/execution/assessment/all"),
    repo: SnapshotRepo = Depends(get_snapshot_repo),
    clock=Depends(get_clock),
) -> JSONResponse:
    if stage is not None and stage not in VALID_STAGES:
        raise BizError(
            ErrorCode.CONTRACT_VALIDATION_FAILED,
            message=f"stage 取值非法：{stage}，仅支持 patrol/prescription/execution/assessment/all。",
        )
    projection = repo.dashboard(farm_no=farmNo)
    if stage is not None:
        projection["stage"] = stage
    envelope = Envelope[dict](
        traceId=trace_id_of(request),
        agentRunId=agent_run_id_of(request),
        data=projection,
        timestamp=iso_now(clock),
    )
    return JSONResponse(
        content=envelope.model_dump(mode="json"),
        headers={"X-Snapshot-At": projection.get("snapshotAt") or ""},
    )