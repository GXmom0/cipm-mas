from __future__ import annotations

import streamlit as st

from apps.console.theme import (
    PRIORITY_HIGH_COLOR,
    PRIORITY_LOW_COLOR,
    PRIORITY_MEDIUM_COLOR,
)

ROLE_ORDER = ("农技专家", "农场管理者", "农户")
ROLE_BY_TYPE = {
    "review": "农技专家",
    "confirm": "农技专家",
    "audit": "农场管理者",
    "replan": "农场管理者",
    "reschedule": "农场管理者",
}

PRIORITY_COLORS = {
    "高": PRIORITY_HIGH_COLOR,
    "中": PRIORITY_MEDIUM_COLOR,
    "低": PRIORITY_LOW_COLOR,
}


def group_todos(todos: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {role: [] for role in ROLE_ORDER}
    for item in todos:
        role = ROLE_BY_TYPE.get(item.get("type", ""), "农场管理者")
        grouped[role].append(item)
    return grouped


def todo_count(todos: list[dict]) -> int:
    return len(todos)


def classify_todo_priority(todo: dict, plots: list[dict]) -> str:
    todo_type = todo.get("type", "")
    plot_no = todo.get("plotNo", "")

    if todo_type in ("review", "confirm"):
        return "高"

    for plot in plots:
        if plot.get("plotNo") == plot_no:
            badges = plot.get("badges") or []
            if "BLOCKED" in badges:
                return "高"
            if "DEGRADED" in badges or "RESCHEDULED" in badges:
                return "中"
            break

    if todo_type in ("audit", "replan"):
        return "中"

    return "低"


def render_todos(todos: list[dict], plots: list[dict] | None = None) -> None:
    if plots is None:
        plots = []
    grouped = group_todos(todos)
    for role in ROLE_ORDER:
        items = grouped[role]
        count = len(items)
        expanded = count > 0
        with st.expander(f"{role}（{count}）", expanded=expanded):
            if not items:
                st.caption("暂无待办")
                continue
            for item in items:
                priority = classify_todo_priority(item, plots)
                priority_color = PRIORITY_COLORS[priority]
                plot_no = item.get("plotNo", "")
                text = item.get("text", "")
                st.markdown(
                    f'<div style="border:1px solid #E0E0E0;border-radius:8px;padding:10px 12px;'
                    f'margin-bottom:6px;display:flex;align-items:center;gap:8px;">'
                    f'<span class="badge-pill" style="background-color:{priority_color}">{priority}</span>'
                    f'<span style="font-weight:600;color:#212121">{plot_no}</span>'
                    f'<span style="color:#616161">{text}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )