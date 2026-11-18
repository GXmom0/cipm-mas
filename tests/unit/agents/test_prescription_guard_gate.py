from __future__ import annotations

from agents.decision.agent import DecisionAgent, DecisionRequest
from domain.models.enums import Phenology, StressType, Toxicity
from domain.models.registry import RegistryItem
from sdk.settings import CipmSettings


def _request(**overrides) -> DecisionRequest:
    item = RegistryItem(
        registry_item_no="R1",
        registry_version="V",
        ai_name="测试药剂",
        formulation="乳油",
        target=StressType.PEST_DISEASE,
        safety_interval_days=7,
        dose_range_ml_per_mu=(1.0, 2.0),
        spray_volume_range_l_per_mu=(1.0, 2.0),
        toxicity=Toxicity.LOW,
    )
    params = dict(
        task_no="T",
        plot_no="PLOT-0912",
        plot_name="测试地块",
        area_mu=1.0,
        remaining_days=30,
        phenology=Phenology.FLOWER_BOLL,
        zones=({"zoneNo": "Z01", "stressLevel": "heavy", "areaMu": 1.0},),
        candidates=(item,),
        drip=True,
    )
    params.update(overrides)
    return DecisionRequest(**params)


def test_generate_refused_when_prerequisites_missing(tmp_path) -> None:
    agent = DecisionAgent(
        settings=CipmSettings(runtime="agent_runtime", audit_dir=str(tmp_path / "audit"))
    )

    result = agent.generate(_request(has_irrigation=False))

    assert result["status"] == "refused"
    assert result["allowed"] is False
    assert result["zones"] == []
    assert result["auditEventId"] is not None
    assert any(v["code"] == "PREREQUISITE_MISSING" for v in result["violations"])