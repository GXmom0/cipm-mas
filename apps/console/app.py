from __future__ import annotations

import streamlit as st

from apps.console.components.alert_card import render_alert_cards
from apps.console.components.batch_queue import render_batch_queue
from apps.console.components.css_inject import inject_custom_css
from apps.console.components.empty_state import render_empty_state
from apps.console.components.metric_card import render_metric_cards_row
from apps.console.components.plot_filter import clear_filter_state, render_plot_filter
from apps.console.components.plot_table import (
    render_action_entries,
    render_action_feedback,
    render_plot_table,
)
from apps.console.components.stress_chart import render_stress_chart
from apps.console.components.todo_panel import render_todos
from apps.console.services.data_source import get_dashboard
from apps.console.services.runtime_state import (
    apply_patrol_baseline,
    clear_runtime_state,
    clear_ui_state,
    merge_stages,
)
from apps.console.theme import (
    PAGE_TITLE,
    TAB_ALERT,
    TAB_OVERVIEW,
    TAB_PRESCRIPTION,
    TAB_SETTINGS,
    TAB_TODO_BATCH,
)

st.set_page_config(page_title=PAGE_TITLE, layout="wide")
inject_custom_css()

settings = None
try:
    from apps.console.config import load_settings

    settings = load_settings()
except Exception:
    settings = None

mock_mode = True if settings is None else settings.mock
api_base = "" if settings is None else settings.api_base

dashboard = get_dashboard(mock=mock_mode, api_base=api_base)

st.title("新疆棉田植保决策多智能体系统")
header_cols = st.columns([2, 2, 1])
if mock_mode:
    header_cols[0].caption("演示模式：CIPM_MOCK=1（零外部依赖）")
else:
    header_cols[0].caption(f"运行模式：{settings.runtime}")

snapshot_at = dashboard.get("snapshotAt")
header_cols[1].caption(f"数据更新于 {snapshot_at}" if snapshot_at else "快照时间未知")

if header_cols[2].button("刷新数据"):
    get_dashboard.clear()
    clear_runtime_state()
    clear_filter_state()
    clear_ui_state()
    st.rerun()

if dashboard.get("degraded"):
    st.warning("数据更新失败，已切换为最近快照")

plots = dashboard.get("plots") or []
if plots:
    apply_patrol_baseline(plots)
    plots = merge_stages(plots)

if not plots:
    render_empty_state()
else:
    todos = dashboard.get("todos") or []
    alerts = dashboard.get("alerts") or []
    batches = dashboard.get("batches") or []

    tabs = st.tabs([TAB_OVERVIEW, TAB_PRESCRIPTION, TAB_TODO_BATCH, TAB_ALERT, TAB_SETTINGS])

    with tabs[0]:
        render_metric_cards_row(len(plots), len(todos), len(alerts), len(batches))
        render_stress_chart(plots)
        filtered_plots = render_plot_filter(plots)
        if filtered_plots:
            st.subheader("四阶段总览")
            render_plot_table(filtered_plots)
            st.subheader("地块操作入口")
            render_action_entries(filtered_plots)
            render_action_feedback()
        else:
            st.info("无匹配地块，请调整筛选条件")

    with tabs[1]:
        render_action_feedback()

    with tabs[2]:
        render_todos(todos, plots)
        render_batch_queue(batches)

    with tabs[3]:
        render_alert_cards(alerts, plots)

    with tabs[4]:
        st.markdown("**运行模式信息**")
        if mock_mode:
            st.info("当前为演示模式（CIPM_MOCK=1），使用本地 Mock 数据，零外部依赖。")
        else:
            st.info(f"当前为运行模式：{settings.runtime}，API 地址：{api_base}")
        st.caption("四阶段：巡田 — 处方 — 作业 — 评估")

st.caption("演示数据为模拟数据，不代表真实农艺建议。")