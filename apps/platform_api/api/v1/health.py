from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from apps.platform_api.core.clock import iso_now
from apps.platform_api.core.deps import get_clock, get_settings
from apps.platform_api.core.trace import agent_run_id_of, trace_id_of
from apps.platform_api.version import VERSION
from sdk.contracts.envelope import Envelope
from sdk.settings import CipmSettings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(
    request: Request,
    settings: CipmSettings = Depends(get_settings),
    clock=Depends(get_clock),
) -> JSONResponse:
    data = {
        "status": "ok",
        "mock": settings.mock,
        "runtime": settings.runtime,
        "version": VERSION,
        "dependencies": {
            "snapshot": "mock",
            "agentarts": "config_only" if settings.agentarts_endpoint else "not_configured",
        },
        "serverTime": iso_now(clock),
    }
    envelope = Envelope[dict](
        traceId=trace_id_of(request),
        agentRunId=agent_run_id_of(request),
        data=data,
        timestamp=iso_now(clock),
    )
    return JSONResponse(content=envelope.model_dump(mode="json"))