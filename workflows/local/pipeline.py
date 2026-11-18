from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agents.assessment.agent import AssessmentAgent
from agents.decision.agent import DecisionAgent, DecisionRequest
from agents.execution.agent import ExecutionAgent
from agents.execution.window_guard import evaluate_for_plot
from agents.patrol.agent import PatrolAgent
from domain.models.enums import Phenology, StressType, Toxicity
from domain.models.registry import RegistryItem
from mock.loader import plot_bundle
from mock.seed import iso_after
from mock.services.recheck_stub import build_recheck
from sdk.settings import CipmSettings

DECISION_STAGE_LABELS = {
    "pending_review": "待审核",
    "approved": "已通过",
    "degraded_pending_confirm": "降级待确认",
    "refused": "已拒绝",
    "rejected": "已驳回",
}


@dataclass(frozen=True)
class PipelineResult:
    plot_no: str
    stages: dict[str, str]
    patrol: dict[str, Any]
    decision: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None
    assessment: dict[str, Any] | None = None
    note: str = ""

    @property
    def completed(self) -> bool:
        return self.stages.get("assessment") in {"达标", "未达标"}


def build_request_for_plot(plot_no: str) -> DecisionRequest:
    bundle = plot_bundle(plot_no)
    plot = bundle["plot"]
    calendar = bundle["calendar"]
    stress = bundle["stressResult"]
    zones = tuple(
        {
            "zoneNo": partition["partitionNo"],
            "stressLevel": partition["stressLevel"],
            "areaMu": partition["areaMu"],
        }
        for partition in stress["partitions"]
        if partition["stressLevel"] != "none"
    )
    candidates = tuple(
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
            target_pest=item.get("targetPest", ""),
            application_method=item.get("applicationMethod", "ground_spray"),
        )
        for item in bundle["registry"]
        if item["valid"]
    )
    return DecisionRequest(
        task_no=stress["taskNo"],
        plot_no=plot["plotNo"],
        plot_name=plot["plotName"],
        area_mu=plot["areaMu"],
        remaining_days=calendar["remainingDays"],
        phenology=Phenology(calendar["phenology"]),
        zones=zones,
        candidates=candidates,
        drip=plot["irrigation"] == "drip",
        target_pest=next(
            (p.get("targetPest") for p in stress.get("partitions", []) if p.get("targetPest")),
            "",
        ),
        block_status=(stress.get("taskBlock") or {}).get("status", "unblocked"),
        stress_result_version=stress.get("resultVersion"),
        has_irrigation=bool(plot.get("irrigation")),
        has_calendar=bool(calendar.get("expectedHarvestDate")),
        has_registry_snapshot=bool(bundle.get("registry")),
        has_weather=True,
    )


def build_demo_feedback(bundle: dict[str, Any], coverage_pct: float = 97.5) -> dict[str, Any]:
    plot = bundle["plot"]
    prescription = bundle["prescription"]
    work_order = bundle.get("workOrder") or {}
    return {
        "schemaVersion": "1.0",
        "workOrderNo": work_order.get("workOrderNo") or f"WO-20261113-{plot['plotNo'].rsplit('-', 1)[-1]}",
        "deviceNo": "DEV-XJ-01",
        "actualAreaMu": plot["areaMu"],
        "coveragePct": coverage_pct,
        "avgFlowLPerMu": 1.6,
        "trackRef": f"obs://cipm-track/{prescription['prescriptionNo']}.json",
        "alarms": [],
        "startedAt": iso_after(days=1, hours=1),
        "completedAt": iso_after(days=1, hours=3),
        "status": "completed",
    }


def run_pipeline(
    plot_no: str,
    settings: Any = None,
    forecast: dict | None = None,
    feedback: dict[str, Any] | None = None,
) -> PipelineResult:
    resolved_settings = settings or CipmSettings(runtime="local", mock=True)
    patrol = PatrolAgent().inspect(plot_no)
    stages = {
        "patrol": "阻断待复核" if patrol.blocked else "已完成",
        "prescription": "已阻断" if patrol.blocked else "未开始",
        "execution": "未开始",
        "assessment": "未开始",
    }
    patrol_summary = {
        "blockStatus": patrol.block_status,
        "blockingPartitions": list(patrol.blocking_partitions),
        "reasonCodes": list(patrol.reason_codes),
        "partitions": [
            {
                "partitionNo": item.partition_no,
                "stressLevel": item.stress_level,
                "confidence": item.confidence,
                "indicators": list(item.indicators),
            }
            for item in patrol.partitions
        ],
    }
    if patrol.blocked:
        return PipelineResult(
            plot_no=plot_no,
            stages=stages,
            patrol=patrol_summary,
            note="识别结果待人工复核，处方生成已暂停。",
        )

    decision = DecisionAgent(resolved_settings, logger=None).generate(build_request_for_plot(plot_no))
    stages["prescription"] = DECISION_STAGE_LABELS.get(decision["status"], decision["status"])
    if not decision["allowed"]:
        return PipelineResult(
            plot_no=plot_no,
            stages=stages,
            patrol=patrol_summary,
            decision=decision,
            note=decision.get("message", "处方未通过校验。"),
        )

    bundle = plot_bundle(plot_no)
    evaluator = (
        (lambda target, region: evaluate_for_plot(target, region, forecast))
        if forecast is not None
        else evaluate_for_plot
    )
    execution = ExecutionAgent(window_evaluator=evaluator).dispatch(
        plot_no, bundle.get("prescription")
    )
    stages["execution"] = {
        "dispatched": "已下发",
        "rescheduled": "待重新排期",
        "rejected": "不可下发",
    }.get(execution.status, execution.status)
    execution_summary = {
        "status": execution.status,
        "message": execution.message,
        "workOrderNo": execution.work_order_no,
        "windowConclusion": execution.window_conclusion,
        "violations": list(execution.violations),
    }
    if execution.status != "dispatched":
        return PipelineResult(
            plot_no=plot_no,
            stages=stages,
            patrol=patrol_summary,
            decision=decision,
            execution=execution_summary,
            note=execution.message,
        )

    after = build_recheck(bundle["stressResult"])
    assessment = AssessmentAgent().assess(
        plot_no=plot_no,
        before_result=bundle["stressResult"],
        after_result=after,
        feedback=feedback or build_demo_feedback(bundle),
        prescription=bundle["prescription"],
    )
    stages["assessment"] = "达标" if assessment.qualified else "未达标"
    return PipelineResult(
        plot_no=plot_no,
        stages=stages,
        patrol=patrol_summary,
        decision=decision,
        execution=execution_summary,
        assessment={
            "verdict": assessment.verdict,
            "coveragePct": assessment.coverage_pct,
            "suppressionRate": assessment.suppression_rate,
            "recommendedAction": assessment.recommended_action,
            "severeZones": list(assessment.severe_zones),
        },
        note="四阶段闭环完成。",
    )