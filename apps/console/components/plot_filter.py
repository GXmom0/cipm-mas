from __future__ import annotations

import streamlit as st

FILTER_STATE_KEY = "cipm_filter_state_v1"

ALL_STAGE_STATUSES = [
    "已完成", "阻断待复核", "识别中", "待接入数据", "数据接入失败",
    "已通过", "待审核", "已阻断", "待作业窗口", "降级待确认", "已驳回", "已拒绝", "草稿", "未开始",
    "已下发", "执行中", "待下发", "待排期", "待重新排期", "已中止", "不可下发",
    "达标", "未达标", "待评估",
]

ALL_BADGE_CODES = ["BLOCKED", "DEGRADED", "REFUSED", "RESCHEDULED"]


def get_filter_state() -> dict:
    return st.session_state.get(
        FILTER_STATE_KEY,
        {"search": "", "stage_filter": [], "badge_filter": []},
    )


def set_filter_state(search: str, stage_filter: list[str], badge_filter: list[str]) -> None:
    st.session_state[FILTER_STATE_KEY] = {
        "search": search,
        "stage_filter": stage_filter,
        "badge_filter": badge_filter,
    }


def clear_filter_state() -> None:
    st.session_state.pop(FILTER_STATE_KEY, None)


def filter_plots(
    plots: list[dict],
    search: str,
    stage_filter: list[str],
    badge_filter: list[str],
) -> list[dict]:
    result = plots
    if search:
        search_lower = search.lower()
        result = [
            plot for plot in result
            if search_lower in plot.get("plotNo", "").lower()
            or search_lower in plot.get("plotName", "").lower()
        ]
    if stage_filter:
        result = [
            plot for plot in result
            if any(
                (plot.get("stages") or {}).get(stage_key, "") in stage_filter
                for stage_key in ("patrol", "prescription", "execution", "assessment")
            )
        ]
    if badge_filter:
        result = [
            plot for plot in result
            if any(badge in (plot.get("badges") or []) for badge in badge_filter)
        ]
    return result


def render_plot_filter(plots: list[dict]) -> list[dict]:
    state = get_filter_state()
    cols = st.columns([2, 1, 1])
    search = cols[0].text_input(
        "搜索地块",
        value=state["search"],
        key="cipm_filter_search",
        placeholder="输入地块编号或名称",
    )
    stage_filter = cols[1].multiselect(
        "阶段筛选",
        options=ALL_STAGE_STATUSES,
        default=state["stage_filter"],
        key="cipm_filter_stage",
    )
    badge_filter = cols[2].multiselect(
        "标识筛选",
        options=ALL_BADGE_CODES,
        default=state["badge_filter"],
        key="cipm_filter_badge",
    )
    set_filter_state(search, stage_filter, badge_filter)
    return filter_plots(plots, search, stage_filter, badge_filter)