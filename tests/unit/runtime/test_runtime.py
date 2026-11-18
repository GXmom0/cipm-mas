from __future__ import annotations

import json
from datetime import datetime

import httpx
import pytest

from agents.decision.agent import DecisionAgent, DecisionRequest
from agents.decision.safety_sandbox import (
    DecisionContext,
    LlmZoneSuggestion,
    PrescriptionSafetySandbox,
)
from apps.platform_api.core.clock import TZ_EAST8, FixedClock
from apps.platform_api.repository.audit_repo import AuditRepo
from domain.models.enums import Phenology, StressType, Toxicity
from domain.models.registry import RegistryItem
from sdk.agent_trace import (
    AGENT_PATROL,
    PATROL_PARSING,
    AgentRunLogger,
)
from sdk.llm_client import (
    LlmMessage,
    MockLlmClient,
    OpenAICompatibleClient,
    extract_json_object,
)
from sdk.settings import CipmSettings

FIXED = datetime(2026, 11, 13, 8, 0, tzinfo=TZ_EAST8)

CATALOG = (
    RegistryItem(
        registry_item_no="XJ-ACE-0381",
        registry_version="XJ-REG-2026.11.01",
        ai_name="啶虫脒",
        formulation="乳油",
        target=StressType.PEST_DISEASE,
        safety_interval_days=7,
        dose_range_ml_per_mu=(10.0, 20.0),
        spray_volume_range_l_per_mu=(1.2, 2.0),
        toxicity=Toxicity.LOW,
    ),
    RegistryItem(
        registry_item_no="XJ-IMI-0453",
        registry_version="XJ-REG-2026.11.01",
        ai_name="吡虫啉",
        formulation="可湿性粉剂",
        target=StressType.PEST_DISEASE,
        safety_interval_days=5,
        dose_range_ml_per_mu=(8.0, 16.0),
        spray_volume_range_l_per_mu=(1.0, 1.8),
        toxicity=Toxicity.LOW,
    ),
)


def _zone(ai_name: str = "啶虫脒", formulation: str = "乳油", item_no: str = "XJ-ACE-0381") -> LlmZoneSuggestion:
    return LlmZoneSuggestion(
        zone_no="Z01",
        ai_name=ai_name,
        formulation=formulation,
        dose_ml_per_mu=12.0,
        spray_volume_l_per_mu=1.6,
        registry_item_no=item_no,
    )


def _context(remaining_days: int = 5) -> DecisionContext:
    return DecisionContext(
        task_no="PT-TEST-0001",
        plot_no="PLOT-0912",
        remaining_days=remaining_days,
        phenology=Phenology.FLOWER_BOLL,
        candidates=CATALOG,
        drip=True,
    )


def _request(remaining_days: int = 5, plot_no: str = "PLOT-0912") -> DecisionRequest:
    return DecisionRequest(
        task_no="PT-20261113-0001",
        plot_no=plot_no,
        plot_name="测试地块",
        area_mu=10.0,
        remaining_days=remaining_days,
        phenology=Phenology.FLOWER_BOLL,
        zones=({"zoneNo": "Z01", "stressLevel": "heavy", "areaMu": 10.0},),
        candidates=CATALOG,
        drip=True,
    )


def _audit(tmp_path) -> AuditRepo:
    return AuditRepo(tmp_path / "audit", FixedClock(FIXED))


def test_sandbox_blocks_safety_interval_violation(tmp_path) -> None:
    repo = _audit(tmp_path)
    sandbox = PrescriptionSafetySandbox(audit_repo=repo)
    result = sandbox.validate(
        (_zone(),),
        _context(remaining_days=5),
        llm_raw={"zones": ["..."]},
        agent_run_id="run_test_001",
    )
    assert result.allowed is False
    assert result.status == "refused"
    assert result.safety_conclusion == "refused"
    assert result.buffer_days == -2
    assert any(item.code == "SAFETY_INTERVAL_REFUSED" for item in result.violations)
    assert result.audit_event_id is not None

    events = repo.all_events()
    assert len(events) == 1
    assert events[0]["eventType"] == "LLM_ERROR"
    assert events[0]["operator"] == "decision_safety_sandbox"
    assert events[0]["result"] == "rejected"
    assert events[0]["bizId"] == "PT-TEST-0001"


def test_sandbox_allows_valid_llm_suggestion(tmp_path) -> None:
    sandbox = PrescriptionSafetySandbox(audit_repo=_audit(tmp_path))
    result = sandbox.validate((_zone(),), _context(remaining_days=20))
    assert result.allowed is True
    assert result.status == "pending_review"
    assert result.safety_conclusion == "satisfied"
    assert result.buffer_days == 13
    assert result.audit_event_id is None


def test_sandbox_intercepts_compound(tmp_path) -> None:
    sandbox = PrescriptionSafetySandbox(audit_repo=_audit(tmp_path))
    zones = (_zone(), _zone(ai_name="吡虫啉", formulation="可湿性粉剂", item_no="XJ-IMI-0453"))
    result = sandbox.validate(zones, _context(remaining_days=20))
    assert result.allowed is False
    assert result.compound_detected is True
    assert any(item.code == "COMPOUND_INTERCEPTED" for item in result.violations)


def test_sandbox_blocks_dose_out_of_range(tmp_path) -> None:
    sandbox = PrescriptionSafetySandbox(audit_repo=_audit(tmp_path))
    zone = LlmZoneSuggestion(
        zone_no="Z01",
        ai_name="啶虫脒",
        formulation="乳油",
        dose_ml_per_mu=40.0,
        spray_volume_l_per_mu=1.6,
        registry_item_no="XJ-ACE-0381",
    )
    result = sandbox.validate((zone,), _context(remaining_days=20))
    assert result.allowed is False
    assert any(item.code == "DOSE_OUT_OF_REGISTRY_RANGE" for item in result.violations)


def test_llm_client_posts_openai_payload() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "deepseek-chat",
                "choices": [{"message": {"content": '{"zones": []}'}}],
                "usage": {"total_tokens": 12},
            },
        )

    client = OpenAICompatibleClient(
        base_url="https://api.example.com/v1",
        model="deepseek-chat",
        api_key="sk-test",
        transport=httpx.MockTransport(handler),
    )
    response = client.chat([LlmMessage(role="user", content="你好")])
    assert captured["url"].endswith("/v1/chat/completions")
    assert captured["auth"] == "Bearer sk-test"
    assert captured["body"]["model"] == "deepseek-chat"
    assert captured["body"]["stream"] is False
    assert response.content == '{"zones": []}'
    assert response.usage["total_tokens"] == 12


def test_llm_client_retries_on_server_error(monkeypatch) -> None:
    monkeypatch.setattr("sdk.llm_client.time.sleep", lambda _: None)
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503, json={"error": "busy"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    client = OpenAICompatibleClient(
        base_url="https://api.example.com/v1",
        model="m",
        max_retries=1,
        transport=httpx.MockTransport(handler),
    )
    response = client.chat([LlmMessage(role="user", content="x")])
    assert calls["count"] == 2
    assert response.content == "{}"


def test_extract_json_from_fenced_output() -> None:
    text = '```json\n{"zones": [{"zoneNo": "Z01"}], "rationale": "ok"}\n```'
    assert extract_json_object(text)["zones"][0]["zoneNo"] == "Z01"


def test_agent_trace_console_format(capsys) -> None:
    logger = AgentRunLogger(agent_run_id="run_demo_001")
    logger.log(AGENT_PATROL, PATROL_PARSING)
    output = capsys.readouterr().out
    assert "[AgentRun: run_demo_001] 巡检Agent 正在解析影像..." in output


def test_decision_agent_runtime_uses_llm(tmp_path) -> None:
    settings = CipmSettings(
        runtime="agentarts",
        mock=False,
        llm_endpoint="https://api.example.com/v1",
        llm_model="deepseek-chat",
    )
    llm = MockLlmClient(
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
            "rationale": "花铃期蚜虫重发",
        }
    )
    repo = _audit(tmp_path)
    agent = DecisionAgent(settings, llm_client=llm, audit_repo=repo, logger=AgentRunLogger(enabled=False))
    result = agent.generate(_request(remaining_days=5))
    assert result["runtime"] == "agentart_runtime"
    assert result["allowed"] is False
    assert result["status"] == "refused"
    assert result["auditEventId"] is not None
    assert [event["eventType"] for event in repo.all_events()] == ["LLM_ERROR"]


def test_decision_agent_runtime_rejects_malformed_output(tmp_path) -> None:
    settings = CipmSettings(
        runtime="agent_runtime",
        mock=False,
        llm_endpoint="https://api.example.com/v1",
        llm_model="m",
    )
    llm = MockLlmClient("这不是 JSON")
    agent = DecisionAgent(settings, llm_client=llm, audit_repo=_audit(tmp_path), logger=AgentRunLogger(enabled=False))
    with pytest.raises(Exception):
        agent.generate(_request())


def test_decision_agent_local_reads_mock(tmp_path) -> None:
    settings = CipmSettings(runtime="local", mock=True)
    agent = DecisionAgent(settings, audit_repo=_audit(tmp_path), logger=AgentRunLogger(enabled=False))
    result = agent.generate(_request(remaining_days=20, plot_no="PLOT-0912"))
    assert result["runtime"] == "local"
    assert result["status"] == "pending_review"
    assert result["allowed"] is True