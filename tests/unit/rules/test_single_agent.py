from __future__ import annotations

import ast
from pathlib import Path

import pytest

from domain.rules import CompoundComponent, RuleInputError, check_single_agent

ROOT = Path(__file__).resolve().parents[3]
FORBIDDEN_IMPORTS = {"requests", "httpx", "os", "random", "datetime", "socket"}


def _component(ai_name: str, formulation: str, interval: int, formulation_type: str = "single") -> CompoundComponent:
    return CompoundComponent(
        ai_name=ai_name,
        formulation=formulation,
        registry_item_no=f"XJ-{ai_name}-{formulation}",
        safety_interval_days=interval,
        formulation_type=formulation_type,
    )


def test_sa00_no_io_imports() -> None:
    for file_name in ("single_agent.py", "types.py"):
        source = (ROOT / "domain" / "rules" / file_name).read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split(".")[0])
        assert not (modules & FORBIDDEN_IMPORTS), f"{file_name} 引入了禁止模块：{modules & FORBIDDEN_IMPORTS}"


def test_sa01_single_allowed() -> None:
    result = check_single_agent((_component("啶虫脒", "乳油", 7),))
    assert result.detected is False
    assert result.allowed is True
    assert result.action == "none"
    assert result.requires_expert_review is False
    assert result.max_safety_interval_days == 7


def test_sa02_two_categories_intercepted() -> None:
    result = check_single_agent(
        (_component("啶虫脒", "乳油", 7), _component("吡虫啉", "可湿性粉剂", 5))
    )
    assert result.detected is True
    assert result.allowed is False
    assert result.action == "intercepted_to_expert"
    assert result.max_safety_interval_days == 7
    assert result.auto_dispatch_allowed is False
    assert result.applies_to == "expert_manual_only"
    assert result.requires_expert_review is True


def test_sa03_three_categories_take_max() -> None:
    result = check_single_agent(
        (
            _component("啶虫脒", "乳油", 7),
            _component("吡虫啉", "可湿性粉剂", 5),
            _component("阿维菌素", "悬浮剂", 10),
        )
    )
    assert result.category_count == 3
    assert result.max_safety_interval_days == 10
    assert "3 个药剂品类" in result.message
    assert result.requires_expert_review is True


def test_sa04_same_ai_different_formulation_counts_two() -> None:
    result = check_single_agent(
        (_component("啶虫脒", "乳油", 7), _component("啶虫脒", "悬浮剂", 7))
    )
    assert result.category_count == 2
    assert result.detected is True
    assert result.allowed is False


def test_sa05_registered_mixture_single_use_allowed() -> None:
    result = check_single_agent(
        (_component("联苯·噻虫嗪", "悬浮剂", 14, formulation_type="mixture_registered"),)
    )
    assert result.detected is False
    assert result.allowed is True
    assert result.action == "none"
    assert result.max_safety_interval_days == 14


@pytest.mark.parametrize("case", ["empty", "blank_ai_name"])
def test_sa06_invalid_input(case: str) -> None:
    with pytest.raises(RuleInputError) as excinfo:
        if case == "empty":
            check_single_agent(())
        else:
            component = CompoundComponent(
                ai_name="", formulation="乳油", registry_item_no="X", safety_interval_days=7
            )
            check_single_agent((component,))
    assert excinfo.value.error_code == "CIPM-RULE-5005"


def test_sa07_idempotent_and_no_release_semantics() -> None:
    components = (_component("啶虫脒", "乳油", 7), _component("吡虫啉", "可湿性粉剂", 5))
    first = check_single_agent(components)
    second = check_single_agent(components)
    assert first == second
    assert components[0].ai_name == "啶虫脒"
    assert not hasattr(first, "approved")
    assert not hasattr(first, "passed")
    assert first.applies_to == "expert_manual_only"