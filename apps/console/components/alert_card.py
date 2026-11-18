from __future__ import annotations

import streamlit as st

from apps.console.theme import PRIORITY_HIGH_COLOR, PRIORITY_LOW_COLOR, PRIORITY_MEDIUM_COLOR

ALERT_SEVERITY_COLORS: dict[str, str] = {
    "high": PRIORITY_HIGH_COLOR,
    "medium": PRIORITY_MEDIUM_COLOR,
    "low": PRIORITY_LOW_COLOR,
}

ALERT_ICONS: dict[str, str] = {
    "high": "❌",
    "medium": "⚠️",
    "low": "ℹ️",
}

ALERT_BG_COLORS: dict[str, str] = {
    "high": "#FFEBEE",
    "medium": "#FFF3E0",
    "low": "#E3F2FD",
}


def classify_alert_severity(alert: dict, plots: list[dict]) -> str:
    plot_no = alert.get("plotNo", "")
    for plot in plots:
        if plot.get("plotNo") == plot_no:
            badges = plot.get("badges") or []
            if "BLOCKED" in badges:
                return "high"
            if "DEGRADED" in badges or "RESCHEDULED" in badges:
                return "medium"
            break
    return "low"


def render_alert_card(alert: dict, plots: list[dict]) -> None:
    severity = classify_alert_severity(alert, plots)
    icon = ALERT_ICONS[severity]
    bg_color = ALERT_BG_COLORS[severity]
    plot_no = alert.get("plotNo", "")
    text = alert.get("text", "")

    st.markdown(
        f'<div style="background-color:{bg_color};border-radius:8px;padding:12px 16px;'
        f'margin-bottom:8px;display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:20px">{icon}</span>'
        f'<span style="font-weight:600;color:#212121">{plot_no}</span>'
        f'<span style="color:#616161">{text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_alert_cards(alerts: list[dict], plots: list[dict]) -> None:
    if not alerts:
        st.info("暂无异常告警")
        return
    st.markdown(f"**异常与告警（{len(alerts)}）**")
    for alert in alerts:
        render_alert_card(alert, plots)