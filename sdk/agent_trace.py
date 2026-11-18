from __future__ import annotations

import secrets
import sys
import time
from typing import Any, TextIO

AGENT_PATROL = "巡检Agent"
AGENT_DECISION = "决策Agent"
AGENT_EXECUTION = "执行Agent"
AGENT_ASSESSMENT = "评估Agent"

PATROL_PARSING = "正在解析影像..."
PATROL_EXPLAIN = "正在生成可解释指标与置信度..."
DECISION_LLM = "正在调用 LLM 生成处方建议..."
DECISION_RULES = "正在执行本地规则校验（单剂复配 + 安全间隔期）..."
DECISION_REFUSED = "LLM 建议被安全沙箱拦截，已写入 LLM_ERROR 审计。"
EXECUTION_DISPATCH = "正在组装作业指令并下发..."
EXECUTION_WAIT = "正在等待设备受理回执..."
ASSESSMENT_REVIEW = "正在回溯作业效果并计算缓解率..."


class AgentRunLogger:
    def __init__(
        self,
        trace_id: str | None = None,
        agent_run_id: str | None = None,
        enabled: bool = True,
        stream: TextIO | None = None,
    ) -> None:
        self.trace_id = trace_id or secrets.token_hex(16)
        self.agent_run_id = agent_run_id or f"run_local_{secrets.token_hex(6)}"
        self.enabled = enabled
        self._stream = stream or sys.stdout
        self._started_at = time.perf_counter()
        self.steps: list[dict[str, Any]] = []

    def log(self, agent: str, action: str, detail: str | None = None) -> dict[str, Any]:
        elapsed_ms = int((time.perf_counter() - self._started_at) * 1000)
        record = {
            "agentRunId": self.agent_run_id,
            "traceId": self.trace_id,
            "agent": agent,
            "action": action,
            "detail": detail,
            "elapsedMs": elapsed_ms,
        }
        self.steps.append(record)
        if self.enabled:
            line = f"[AgentRun: {self.agent_run_id}] {agent} {action}"
            if detail:
                line = f"{line} {detail}"
            print(line, file=self._stream, flush=True)
        return record

    def transition(self, from_agent: str, to_agent: str, reason: str = "") -> None:
        detail = f"-> {to_agent}" if not reason else f"-> {to_agent}（{reason}）"
        self.log(from_agent, "完成，流转至下一节点", detail)

    def as_dict(self) -> dict[str, Any]:
        return {
            "agentRunId": self.agent_run_id,
            "traceId": self.trace_id,
            "steps": list(self.steps),
        }