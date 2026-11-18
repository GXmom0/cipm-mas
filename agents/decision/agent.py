from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from agents.decision.safety_sandbox import (
    DecisionContext,
    LlmZoneSuggestion,
    PrescriptionSafetySandbox,
    SandboxResult,
)
from domain.models.enums import Phenology
from domain.models.registry import RegistryItem
from domain.rules.prescription_guard import (
    GuardResult,
    PrerequisiteInput,
    check_prerequisites,
)
from sdk.agent_trace import (
    AGENT_DECISION,
    DECISION_LLM,
    DECISION_REFUSED,
    DECISION_RULES,
    AgentRunLogger,
)
from sdk.llm_client import (
    LlmClient,
    LlmMessage,
    LlmOutputFormatError,
    build_llm_client,
    extract_json_object,
)
from sdk.runtime_mode import is_agent_runtime
from sdk.settings import CipmSettings

SYSTEM_PROMPT = """你是新疆棉田植保决策专家。你只能基于给定的登记用药目录候选生成单剂处方建议。
硬性约束：
1. 每个分区只能选择一种药剂（有效成分 + 剂型），V1.0 不支持任何复配。
2. 所有药剂必须来自给定 registryCandidates，不得虚构登记证号、剂量区间或安全间隔期。
3. 制剂亩用量、喷液量或稀释浓度三项必须齐备，且稀释倍数需满足：稀释倍数 = 喷液量(mL/亩) ÷ 制剂亩用量(mL/亩)。
4. 滴灌棉田喷液量不得超过目录区间中值。
5. 安全间隔期由系统规则引擎判定，你不得声称已通过安全间隔校验。
只输出 JSON 对象，不要输出 Markdown 或解释性前后缀。JSON 结构：
{"zones":[{"zoneNo":"Z01","aiName":"啶虫脒","formulation":"乳油","registryItemNo":"XJ-ACE-0381",
"doseMlPerMu":12.0,"sprayVolumeLPerMu":1.6,"dilutionRatio":null}],"rationale":"简要说明"}"""


@dataclass(frozen=True)
class DecisionRequest:
    task_no: str
    plot_no: str
    plot_name: str
    area_mu: float
    remaining_days: int
    phenology: Phenology
    zones: tuple[dict[str, Any], ...]
    candidates: tuple[RegistryItem, ...]
    drip: bool = True
    same_ai_used_within_interval: bool = False
    season_usage_exceeded: bool = False
    pre_harvest_sensitive: bool = False
    days_since_last_same_ai: int | None = None
    rotation_interval_days: int | None = None
    target_pest: str = ""
    block_status: str = "unblocked"
    stress_result_version: int | None = 1
    has_irrigation: bool = True
    has_calendar: bool = True
    has_registry_snapshot: bool = True
    has_weather: bool = True


class DecisionAgent:
    def __init__(
        self,
        settings: CipmSettings,
        llm_client: LlmClient | None = None,
        sandbox: PrescriptionSafetySandbox | None = None,
        audit_repo: Any | None = None,
        logger: AgentRunLogger | None = None,
    ) -> None:
        self.settings = settings
        self._llm = llm_client
        if audit_repo is None:
            from apps.platform_api.core.clock import SystemClock
            from apps.platform_api.repository.audit_repo import AuditRepo

            audit_repo = AuditRepo(settings.audit_dir, SystemClock())
        self._sandbox = sandbox or PrescriptionSafetySandbox(audit_repo=audit_repo)
        self._audit = audit_repo
        self.logger = logger or AgentRunLogger(enabled=False)

    @property
    def llm(self) -> LlmClient:
        if self._llm is None:
            self._llm = build_llm_client(self.settings)
        return self._llm

    def generate(self, request: DecisionRequest) -> dict[str, Any]:
        if is_agent_runtime(self.settings):
            return self._generate_runtime(request)
        return self._generate_local(request)

    @staticmethod
    def _filter_candidates(
        candidates: tuple[RegistryItem, ...], target_pest: str
    ) -> tuple[RegistryItem, ...]:
        if not target_pest:
            return candidates
        return tuple(
            item
            for item in candidates
            if not item.target_pest or item.target_pest == target_pest
        )

    def _generate_runtime(self, request: DecisionRequest) -> dict[str, Any]:
        guard = check_prerequisites(
            PrerequisiteInput(
                block_status=request.block_status,
                stress_result_version=request.stress_result_version,
                has_irrigation=request.has_irrigation,
                has_calendar=request.has_calendar,
                has_registry_snapshot=request.has_registry_snapshot,
                has_weather=request.has_weather,
            )
        )
        if guard.blocked:
            self.logger.log(AGENT_DECISION, DECISION_REFUSED, "prerequisite_missing")
            return self._prerequisite_blocked_payload(request, guard)
        candidates = self._filter_candidates(request.candidates, request.target_pest)
        if not candidates:
            self.logger.log(AGENT_DECISION, DECISION_REFUSED, "no_eligible_item")
            return self._no_eligible_payload(request)
        self.logger.log(AGENT_DECISION, DECISION_LLM, f"model={self.settings.llm_model}")
        messages = [
            LlmMessage(role="system", content=SYSTEM_PROMPT),
            LlmMessage(role="user", content=self._user_prompt(request)),
        ]
        response = self.llm.chat(messages)
        payload = extract_json_object(response.content)
        zones = self._parse_zones(payload)
        self.logger.log(
            AGENT_DECISION,
            DECISION_RULES,
            f"zones={len(zones)} candidates={len(candidates)}",
        )
        context = DecisionContext(
            task_no=request.task_no,
            plot_no=request.plot_no,
            remaining_days=request.remaining_days,
            phenology=request.phenology,
            candidates=candidates,
            drip=request.drip,
            target_pest=request.target_pest,
            same_ai_used_within_interval=request.same_ai_used_within_interval,
            season_usage_exceeded=request.season_usage_exceeded,
            pre_harvest_sensitive=request.pre_harvest_sensitive,
            days_since_last_same_ai=request.days_since_last_same_ai,
            rotation_interval_days=request.rotation_interval_days,
        )
        result = self._sandbox.validate(
            zones,
            context,
            llm_raw=payload,
            agent_run_id=self.logger.agent_run_id,
            trace_id=self.logger.trace_id,
        )
        if not result.allowed:
            self.logger.log(AGENT_DECISION, DECISION_REFUSED, f"audit={result.audit_event_id or '未写入'}")
        return self._result_payload(request, result, response.model, payload)

    def _no_eligible_payload(self, request: DecisionRequest) -> dict[str, Any]:
        audit_id = None
        if self._audit is not None:
            audit_id = self._audit.append(
                "DECISION_REFUSED",
                "decision_agent",
                biz_id=request.task_no,
                after={
                    "reasonCode": "NO_ELIGIBLE_CANDIDATE",
                    "targetPest": request.target_pest,
                    "plotNo": request.plot_no,
                    "candidateCount": len(request.candidates),
                    "filteredCount": 0,
                },
                result="rejected",
            )
        return {
            "runtime": "agentart_runtime",
            "agent": AGENT_DECISION,
            "plotNo": request.plot_no,
            "status": "refused",
            "allowed": False,
            "safetyCheck": None,
            "zones": [],
            "violations": [
                {
                    "code": "NO_ELIGIBLE_ITEM",
                    "message": "登记用药目录中无对症药剂，已拒绝自动生成处方，转专家/农技人员人工处置。",
                    "zoneNo": None,
                }
            ],
            "compoundDetected": False,
            "maxSafetyIntervalDays": None,
            "auditEventId": audit_id,
            "message": "无对症登记药剂：拒绝自动生成处方，转专家处理。",
            "rationale": "",
        }

    def _prerequisite_blocked_payload(
        self, request: DecisionRequest, guard: GuardResult
    ) -> dict[str, Any]:
        audit_id = None
        if self._audit is not None:
            audit_id = self._audit.append(
                "DECISION_REFUSED",
                "decision_agent",
                biz_id=request.task_no,
                after={
                    "reasonCode": "PREREQUISITE_MISSING",
                    "plotNo": request.plot_no,
                    "targetPest": request.target_pest,
                    "missingItems": list(guard.missing_items),
                    "reasonCodes": list(guard.reason_codes),
                },
                result="rejected",
            )
        return {
            "runtime": "agentart_runtime",
            "agent": AGENT_DECISION,
            "plotNo": request.plot_no,
            "status": "refused",
            "allowed": False,
            "safetyCheck": None,
            "zones": [],
            "violations": [
                {
                    "code": "PREREQUISITE_MISSING",
                    "message": guard.message,
                    "zoneNo": None,
                }
            ],
            "compoundDetected": False,
            "maxSafetyIntervalDays": None,
            "auditEventId": audit_id,
            "message": guard.message,
            "rationale": "",
        }

    def _generate_local(self, request: DecisionRequest) -> dict[str, Any]:
        from mock.loader import plot_bundle

        self.logger.log(AGENT_DECISION, "读取本地 Mock 数据集生成处方（演示模式）")
        bundle = plot_bundle(request.plot_no)
        prescription = bundle.get("prescription")
        if prescription is None:
            raise LookupError(f"Mock 数据集未找到地块 {request.plot_no} 的处方")
        return {
            "runtime": "local",
            "agent": AGENT_DECISION,
            "plotNo": request.plot_no,
            "status": prescription["status"],
            "allowed": prescription["status"] != "refused",
            "zones": prescription["zones"],
            "safetyCheck": prescription["safetyCheck"],
            "violations": [],
            "auditEventId": None,
            "message": "本地演示模式：使用 Mock 处方数据，未调用大模型。",
        }

    def _user_prompt(self, request: DecisionRequest) -> str:
        context = {
            "taskNo": request.task_no,
            "plotNo": request.plot_no,
            "plotName": request.plot_name,
            "areaMu": request.area_mu,
            "remainingDays": request.remaining_days,
            "phenology": request.phenology.value,
            "irrigation": "drip" if request.drip else "non_drip",
            "zones": list(request.zones),
            "registryCandidates": [
                {
                    "registryItemNo": item.registry_item_no,
                    "aiName": item.ai_name,
                    "formulation": item.formulation,
                    "safetyIntervalDays": item.safety_interval_days,
                    "doseRangeMlPerMu": list(item.dose_range_ml_per_mu),
                    "sprayVolumeRangeLPerMu": list(item.spray_volume_range_l_per_mu),
                    "toxicity": item.toxicity.value,
                    "target": item.target.value,
                }
                for item in self._filter_candidates(request.candidates, request.target_pest)
            ],
        }
        return json.dumps(context, ensure_ascii=False)

    def _parse_zones(self, payload: dict[str, Any]) -> tuple[LlmZoneSuggestion, ...]:
        raw_zones = payload.get("zones")
        if not isinstance(raw_zones, list) or not raw_zones:
            raise LlmOutputFormatError("LLM 建议缺少非空 zones 数组")
        zones = []
        for raw in raw_zones:
            if not isinstance(raw, dict):
                raise LlmOutputFormatError("zones 元素必须为对象")
            zone_no = str(raw.get("zoneNo") or raw.get("zone_no") or "")
            if not zone_no:
                raise LlmOutputFormatError("zone 缺少 zoneNo")
            try:
                zones.append(
                    LlmZoneSuggestion(
                        zone_no=zone_no,
                        ai_name=str(raw.get("aiName") or raw.get("ai_name") or ""),
                        formulation=str(raw.get("formulation") or ""),
                        dose_ml_per_mu=float(raw.get("doseMlPerMu") or raw.get("dose_ml_per_mu") or 0),
                        spray_volume_l_per_mu=self._optional_float(
                            raw.get("sprayVolumeLPerMu") or raw.get("spray_volume_l_per_mu")
                        ),
                        dilution_ratio=self._optional_float(
                            raw.get("dilutionRatio") or raw.get("dilution_ratio")
                        ),
                        registry_item_no=str(raw.get("registryItemNo") or raw.get("registry_item_no") or ""),
                        safety_interval_days=raw.get("safetyIntervalDays"),
                        zero_application=bool(raw.get("zeroApplication", False)),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise LlmOutputFormatError(f"zone 字段类型错误：{exc}") from exc
        return tuple(zones)

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None or value == "":
            return None
        return float(value)

    def _result_payload(
        self,
        request: DecisionRequest,
        result: SandboxResult,
        model: str,
        llm_payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "runtime": "agentart_runtime",
            "agent": AGENT_DECISION,
            "model": model,
            "plotNo": request.plot_no,
            "status": result.status,
            "allowed": result.allowed,
            "safetyCheck": {
                "conclusion": result.safety_conclusion,
                "remainingDays": result.remaining_days,
                "safetyIntervalDays": result.safety_interval_days,
                "bufferDays": result.buffer_days,
                "degradeReasons": list(result.degrade_reasons),
                "requiresExpertConfirm": result.requires_expert_confirm,
            },
            "zones": [asdict(zone) for zone in result.zones],
            "violations": [asdict(item) for item in result.violations],
            "compoundDetected": result.compound_detected,
            "maxSafetyIntervalDays": result.max_safety_interval_days,
            "auditEventId": result.audit_event_id,
            "message": result.message,
            "rationale": llm_payload.get("rationale", ""),
            "agentRunId": self.logger.agent_run_id,
        }