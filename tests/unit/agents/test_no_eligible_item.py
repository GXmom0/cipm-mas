from __future__ import annotations

from agents.decision.agent import DecisionAgent, DecisionRequest
from domain.models.enums import Phenology, StressType, Toxicity
from domain.models.registry import RegistryItem
from sdk.settings import CipmSettings


def test_pest_without_registered_item_is_refused(tmp_path) -> None:
    item = RegistryItem(
        registry_item_no="R-OTHER-PEST",
        registry_version="V",
        ai_name="棉铃虫专用药剂",
        formulation="乳油",
        target=StressType.PEST_DISEASE,
        safety_interval_days=7,
        dose_range_ml_per_mu=(1.0, 2.0),
        spray_volume_range_l_per_mu=(1.0, 2.0),
        toxicity=Toxicity.LOW,
        target_pest="棉铃虫",
    )
    request = DecisionRequest(
        task_no="T",
        plot_no="PLOT-0912",
        plot_name="测试地块",
        area_mu=1.0,
        remaining_days=30,
        phenology=Phenology.FLOWER_BOLL,
        zones=({"zoneNo": "Z01", "stressLevel": "heavy", "areaMu": 1.0},),
        candidates=(item,),
        drip=True,
        target_pest="棉蚜",
    )
    agent = DecisionAgent(
        settings=CipmSettings(runtime="agent_runtime", audit_dir=str(tmp_path / "audit"))
    )

    result = agent.generate(request)

    assert result["status"] == "refused"
    assert result["allowed"] is False
    assert result["zones"] == []
    assert any(v["code"] == "NO_ELIGIBLE_ITEM" for v in result["violations"])
    assert result["auditEventId"] is not None

def test_no_eligible_item_writes_audit_event(tmp_path) -> None:
    from datetime import datetime

    from apps.platform_api.core.clock import TZ_EAST8, FixedClock
    from apps.platform_api.repository.audit_repo import AuditRepo

    repo = AuditRepo(tmp_path / "audit", FixedClock(datetime(2026, 11, 13, 8, 0, tzinfo=TZ_EAST8)))
    item = RegistryItem(
        registry_item_no="R-OTHER-PEST",
        registry_version="V",
        ai_name="棉铃虫专用药剂",
        formulation="乳油",
        target=StressType.PEST_DISEASE,
        safety_interval_days=7,
        dose_range_ml_per_mu=(1.0, 2.0),
        spray_volume_range_l_per_mu=(1.0, 2.0),
        toxicity=Toxicity.LOW,
        target_pest="棉铃虫",
    )
    request = DecisionRequest(
        task_no="T-AUDIT",
        plot_no="PLOT-0912",
        plot_name="测试地块",
        area_mu=1.0,
        remaining_days=30,
        phenology=Phenology.FLOWER_BOLL,
        zones=({"zoneNo": "Z01", "stressLevel": "heavy", "areaMu": 1.0},),
        candidates=(item,),
        drip=True,
        target_pest="棉蚜",
    )
    agent = DecisionAgent(settings=CipmSettings(runtime="agent_runtime"), audit_repo=repo)

    result = agent.generate(request)

    assert result["auditEventId"] is not None
    events = repo.all_events()
    assert len(events) == 1
    event = events[0]
    assert event["eventType"] == "DECISION_REFUSED"
    assert event["afterValue"]["reasonCode"] == "NO_ELIGIBLE_CANDIDATE"
    assert event["afterValue"]["targetPest"] == "棉蚜"
    assert event["afterValue"]["plotNo"] == "PLOT-0912"
    assert event["afterValue"]["candidateCount"] == 1
    assert event["afterValue"]["filteredCount"] == 0