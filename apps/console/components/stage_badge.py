from __future__ import annotations

import streamlit as st

from apps.console.theme import BADGE_COLORS, BADGE_LABELS, UNKNOWN_BADGE_LABEL


def badge_label(code: str) -> str:
    return BADGE_LABELS.get(code, UNKNOWN_BADGE_LABEL)


def badge_color(code: str) -> str:
    return BADGE_COLORS.get(code, "#757575")


def render_badge(code: str) -> None:
    label = badge_label(code)
    color = badge_color(code)
    st.markdown(
        f'<span class="badge-pill" style="background-color:{color}">{label}</span>',
        unsafe_allow_html=True,
    )


def render_badge_html(code: str) -> str:
    label = badge_label(code)
    color = badge_color(code)
    return f'<span class="badge-pill" style="background-color:{color}">{label}</span>'


def render_badges(codes: list[str]) -> None:
    if not codes:
        st.caption("无异常标识")
        return
    for code in codes:
        render_badge(code)