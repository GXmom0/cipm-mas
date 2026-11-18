from __future__ import annotations

import copy
from typing import Any

import streamlit as st

STATE_KEY = "cipm_runtime_state_v1"
BASELINE_KEY = "cipm_patrol_baseline_v1"
STAGES = ("patrol", "prescription", "execution", "assessment")


def _state() -> dict[str, dict[str, str]]:
    return st.session_state.setdefault(STATE_KEY, {})


def set_stage(plot_no: str, stage: str, value: str) -> None:
    if stage not in STAGES:
        raise ValueError(f"未知阶段：{stage}")
    _state().setdefault(plot_no, {})[stage] = value


def stage_of(plot_no: str, stage: str) -> str | None:
    return _state().get(plot_no, {}).get(stage)


def merge_stages(plots: list[dict]) -> list[dict]:
    merged = []
    for plot in plots:
        item = copy.deepcopy(plot)
        stages = dict(item.get("stages") or {})
        stages.update(_state().get(item.get("plotNo", ""), {}))
        item["stages"] = stages
        merged.append(item)
    return merged


def apply_patrol_baseline(plots: list[dict]) -> None:
    if st.session_state.get(BASELINE_KEY):
        return
    from agents.patrol.agent import PatrolAgent

    agent = PatrolAgent()
    for plot in plots:
        plot_no = plot.get("plotNo", "")
        try:
            result = agent.inspect(plot_no)
        except (KeyError, LookupError, ValueError):
            continue
        set_stage(plot_no, "patrol", "阻断待复核" if result.blocked else "已完成")
        if result.blocked:
            set_stage(plot_no, "prescription", "已阻断")
    st.session_state[BASELINE_KEY] = True


UI_STATE_KEYS = (
    "cipm_filter_state_v1",
    "cipm_active_tab_v1",
    "cipm_prescription_expanded_v1",
    "cipm_dispatch_expanded_v1",
    "cipm_todo_collapsed_v1",
    "cipm_batch_sort_v1",
)


def clear_filter_state() -> None:
    st.session_state.pop("cipm_filter_state_v1", None)


def clear_ui_state() -> None:
    for key in UI_STATE_KEYS:
        st.session_state.pop(key, None)


def clear_runtime_state() -> None:
    st.session_state.pop(STATE_KEY, None)
    st.session_state.pop(BASELINE_KEY, None)