from __future__ import annotations

import argparse
from dataclasses import replace
from typing import Any

from agents.decision.agent import DecisionAgent, DecisionRequest
from domain.models.enums import Phenology, StressType, Toxicity
from domain.models.registry import RegistryItem
from sdk.agent_trace import (
    AGENT_ASSESSMENT,
    AGENT_DECISION,
    AGENT_EXECUTION,
    AGENT_PATROL,
    ASSESSMENT_REVIEW,
    EXECUTION_DISPATCH,
    EXECUTION_WAIT,
    PATROL_EXPLAIN,
    PATROL_PARSING,
    AgentRunLogger,
)
from sdk.runtime_mode import is_agent_runtime
from sdk.settings import CipmSettings


def build_request(scenario_id: str = "normal_plot") -> DecisionRequest:
    from mock.loader import load_scenario

    dataset = load_scenario(scenario_id)
    plot = dataset["plots"][0]
    calendar = dataset["calendar"][plot["plotNo"]]
    stress = dataset["stressResults"][0]
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
        for item in dataset["registry"]
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
        has_registry_snapshot=bool(dataset.get("registry")),
        has_weather=True,
    )


def run_demo(
    scenario_id: str = "normal_plot",
    settings: CipmSettings | None = None,
    llm_client: Any = None,
    audit_repo: Any = None,
    quiet: bool = False,
) -> dict[str, Any]:
    resolved = settings or CipmSettings.from_env()
    logger = AgentRunLogger(enabled=not quiet)
    request = build_request(scenario_id)

    logger.log(AGENT_PATROL, PATROL_PARSING, f"plot={request.plot_no}")
    logger.log(AGENT_PATROL, PATROL_EXPLAIN, "NDVI 偏离与虫口密度已生成，置信度已校验")
    logger.transition(AGENT_PATROL, AGENT_DECISION, "识别结果已冻结")

    agent = DecisionAgent(
        resolved,
        llm_client=llm_client,
        audit_repo=audit_repo,
        logger=logger,
    )
    decision = agent.generate(request)

    if decision["allowed"]:
        logger.transition(AGENT_DECISION, AGENT_EXECUTION, "本地规则沙箱校验通过")
        work_order_no = f"WO-20261113-{request.task_no[-4:]}"
        logger.log(AGENT_EXECUTION, EXECUTION_DISPATCH, f"workOrder={work_order_no}")
        logger.log(AGENT_EXECUTION, EXECUTION_WAIT, "设备受理回执已返回")
        logger.transition(AGENT_EXECUTION, AGENT_ASSESSMENT, "作业完成，回传数据已入库")
        logger.log(AGENT_ASSESSMENT, ASSESSMENT_REVIEW, "覆盖率与缓解率待计算")
    else:
        logger.log(
            AGENT_EXECUTION,
            "作业下发已中止",
            "上游处方被安全沙箱拦截，未产生设备指令",
        )

    return {
        "scenarioId": scenario_id,
        "runtime": resolved.runtime,
        "decision": decision,
        "agentRun": logger.as_dict(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="四 Agent 流转演示（本地 Mock 或云端 LLM）")
    parser.add_argument("--scenario", default="normal_plot", choices=["normal_plot", "low_confidence_plot", "safety_conflict_plot"])
    parser.add_argument("--runtime", default=None, help="覆盖 CIPM_RUNTIME，如 agentarts")
    parser.add_argument("--demo-llm", action="store_true", help="使用内置回放 LLM 演示运行时链路，不联网")
    parser.add_argument("--quiet", action="store_true", help="不打印 AgentRun 日志")
    args = parser.parse_args(argv)

    settings = CipmSettings.from_env()
    if args.runtime:
        settings = replace(settings, runtime=args.runtime)

    llm_client = None
    if args.demo_llm:
        from sdk.llm_client import MockLlmClient

        settings = replace(settings, runtime="agentarts", mock=False, llm_model="mock-replay")
        llm_client = MockLlmClient(
            {
                "zones": [
                    {
                        "zoneNo": "Z01",
                        "aiName": "啶虫脒",
                        "formulation": "乳油",
                        "registryItemNo": "XJ-ACE-0381",
                        "doseMlPerMu": 12.0,
                        "sprayVolumeLPerMu": 1.6,
                    }
                ],
                "rationale": "内置回放示例：花铃期蚜虫重发，选用低毒单剂。",
            }
        )

    if is_agent_runtime(settings) and not settings.llm_endpoint and not args.demo_llm:
        print("运行时模式缺少 CIPM_LLM_ENDPOINT，请先配置 .env 或环境变量。")
        return 2

    from apps.platform_api.core.clock import SystemClock
    from apps.platform_api.repository.audit_repo import AuditRepo

    audit_repo = AuditRepo(settings.audit_dir, SystemClock())
    result = run_demo(
        args.scenario,
        settings=settings,
        llm_client=llm_client,
        audit_repo=audit_repo,
        quiet=args.quiet,
    )
    decision = result["decision"]
    print(f"决策结论：{decision['status']}；沙箱放行：{decision['allowed']}")
    if decision.get("auditEventId"):
        print(f"LLM_ERROR 审计：{decision['auditEventId']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())