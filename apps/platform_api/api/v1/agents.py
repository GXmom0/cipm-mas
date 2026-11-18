from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from agents.decision.agent import DecisionAgent, DecisionRequest
from apps.platform_api.core.clock import iso_now
from apps.platform_api.core.deps import get_audit_repo, get_clock, get_settings
from apps.platform_api.core.errors import BizError
from apps.platform_api.core.trace import trace_id_of
from domain.models.enums import Phenology, StressType, Toxicity
from domain.models.registry import RegistryItem
from sdk.agent_trace import AgentRunLogger
from sdk.contracts.common import StrictModel
from sdk.contracts.envelope import Envelope
from sdk.contracts.error_codes import ErrorCode
from sdk.runtime_mode import is_agent_runtime
from sdk.settings import CipmSettings

router = APIRouter(tags=["agents"])


class ZoneInput(StrictModel):
    zoneNo: str = Field(min_length=1)
    stressLevel: str = Field(default="medium")
    areaMu: float = Field(default=1.0, gt=0)


class DecisionInvokeRequest(StrictModel):
    taskNo: str = Field(min_length=1)
    plotNo: str = Field(min_length=1)
    plotName: str = ""
    areaMu: float = Field(default=0, ge=0)
    remainingDays: int = Field(ge=0)
    phenology: str = Field(default="flower_boll")
    irrigation: str = Field(default="drip")
    zones: list[ZoneInput] = Field(min_length=1)


def _registry_candidates() -> tuple[RegistryItem, ...]:
    from mock.services.registry_stub import list_items

    return tuple(
        RegistryItem(
            registry_item_no=item["registryItemNo"],
            registry_version=item["registryVersion"],
            ai_name=item["category"]["aiName"],
            formulation=item["category"]["formulation"],
            target=StressType(item["target"]),
            safety_interval_days=item["safetyIntervalDays"],
            dose_range_ml_per_mu=tuple(item["doseRangeMlPerMu"]),
            spray_volume_range_l_per_mu=tuple(item["sprayVolumeRangeLPerMu"]),
            toxicity=Toxicity(item["toxicity"]),
            registration_no=item["registrationNo"],
            formulation_type=item.get("formulationType", "single"),
        )
        for item in list_items()
    )


@router.post("/agents/decision/invoke")
def invoke_decision(
    payload: DecisionInvokeRequest,
    request: Request,
    settings: CipmSettings = Depends(get_settings),
    audit_repo: Any = Depends(get_audit_repo),
    clock=Depends(get_clock),
) -> JSONResponse:
    if not is_agent_runtime(settings):
        raise BizError(
            ErrorCode.SYSTEM_UNAVAILABLE,
            message="当前为 local 演示模式，LLM 决策接口仅在 CIPM_RUNTIME=agentarts 时可用。",
            http_status=409,
        )
    if not settings.llm_endpoint or not settings.llm_model:
        raise BizError(
            ErrorCode.SYSTEM_UNAVAILABLE,
            message="运行时模式缺少 CIPM_LLM_ENDPOINT 或 CIPM_LLM_MODEL。",
            http_status=503,
        )

    logger = AgentRunLogger(
        trace_id=trace_id_of(request),
        enabled=True,
    )
    agent = DecisionAgent(settings, audit_repo=audit_repo, logger=logger)
    decision_request = DecisionRequest(
        task_no=payload.taskNo,
        plot_no=payload.plotNo,
        plot_name=payload.plotName,
        area_mu=payload.areaMu,
        remaining_days=payload.remainingDays,
        phenology=Phenology(payload.phenology),
        zones=tuple(zone.model_dump() for zone in payload.zones),
        candidates=_registry_candidates(),
        drip=payload.irrigation == "drip",
    )
    result = agent.generate(decision_request)
    envelope = Envelope[dict](
        traceId=trace_id_of(request),
        agentRunId=logger.agent_run_id,
        bizId=payload.taskNo,
        data=result,
        timestamp=iso_now(clock),
    )
    return JSONResponse(content=envelope.model_dump(mode="json"))