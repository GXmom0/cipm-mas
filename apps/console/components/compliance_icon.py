from __future__ import annotations

import streamlit as st

from apps.console.theme import STATUS_BLOCKED, STATUS_DEGRADED, NODE_DONE_COLOR

SAFETY_ICON_MAP: dict[str, tuple[str, str]] = {
    "satisfied": ("✅", NODE_DONE_COLOR),
    "degraded": ("⚠️", STATUS_DEGRADED),
    "refused": ("❌", STATUS_BLOCKED),
}
WINDOW_ICON_MAP: dict[str, tuple[str, str]] = {
    "pass": ("✅", NODE_DONE_COLOR),
    "pass_with_mandatory_notice": ("⚠️", STATUS_DEGRADED),
    "fail": ("❌", STATUS_BLOCKED),
}

SAFETY_LABELS = {"satisfied": "满足", "degraded": "降级", "refused": "拒绝"}
WINDOW_LABELS = {
    "pass": "通过",
    "pass_with_mandatory_notice": "通过（带强制提示）",
    "fail": "不通过",
}


def render_safety_icon(conclusion: str) -> None:
    icon, color = SAFETY_ICON_MAP.get(conclusion, ("❓", "#9E9E9E"))
    label = SAFETY_LABELS.get(conclusion, conclusion)
    st.markdown(
        f'<span style="color:{color};font-size:16px;font-weight:600">{icon} {label}</span>',
        unsafe_allow_html=True,
    )


def render_window_icon(conclusion: str) -> None:
    icon, color = WINDOW_ICON_MAP.get(conclusion, ("❓", "#9E9E9E"))
    label = WINDOW_LABELS.get(conclusion, conclusion)
    st.markdown(
        f'<span style="color:{color};font-size:16px;font-weight:600">{icon} {label}</span>',
        unsafe_allow_html=True,
    )