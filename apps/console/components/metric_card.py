from __future__ import annotations

import streamlit as st

from apps.console.theme import (
    BUFFER_DANGER_COLOR,
    BUFFER_SAFE_COLOR,
    BUFFER_WARNING_COLOR,
)


def buffer_color(buffer_value: int | float) -> str:
    if buffer_value < 0:
        return BUFFER_DANGER_COLOR
    if buffer_value < 3:
        return BUFFER_WARNING_COLOR
    return BUFFER_SAFE_COLOR


def render_metric_card(
    label: str,
    value: int | str,
    icon: str,
    trend: str = "",
    description: str = "",
    color_override: str = "",
) -> None:
    accent = color_override or "#2E7D32"
    trend_icon = ""
    if trend == "上升":
        trend_icon = " ↑"
    elif trend == "下降":
        trend_icon = " ↓"
    with st.container(border=True):
        cols = st.columns([1, 3])
        cols[0].markdown(f"<div style='font-size:28px;text-align:center'>{icon}</div>", unsafe_allow_html=True)
        cols[1].markdown(
            f"<div style='font-size:12px;color:#757575'>{label}</div>"
            f"<div style='font-size:22px;font-weight:700;color:{accent}'>{value}{trend_icon}</div>"
            f"<div style='font-size:11px;color:#9E9E9E'>{description}</div>",
            unsafe_allow_html=True,
        )


def render_metric_cards_row(
    plots_count: int,
    todos_count: int,
    alerts_count: int,
    batches_count: int,
) -> None:
    cols = st.columns(4)
    with cols[0]:
        render_metric_card("地块总数", plots_count, "🌾", description="巡田—处方—作业—评估")
    with cols[1]:
        render_metric_card("待办总数", todos_count, "📋", description="按角色分组")
    with cols[2]:
        render_metric_card("异常总数", alerts_count, "⚠️", description="需关注告警")
    with cols[3]:
        render_metric_card("批次总数", batches_count, "📦", description="作业调度队列")