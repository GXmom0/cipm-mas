from __future__ import annotations

import streamlit as st

from apps.console.theme import (
    BATCH_STATE_COLORS,
    BATCH_STATE_LABELS,
    URGENCY_HEAT_HIGH,
    URGENCY_HEAT_LOW,
)

BATCH_SORT_KEY = "cipm_batch_sort_v1"


def _interpolate_color(low: str, high: str, ratio: float) -> str:
    low_r = int(low[1:3], 16)
    low_g = int(low[3:5], 16)
    low_b = int(low[5:7], 16)
    high_r = int(high[1:3], 16)
    high_g = int(high[3:5], 16)
    high_b = int(high[5:7], 16)
    r = int(low_r + (high_r - low_r) * ratio)
    g = int(low_g + (high_g - low_g) * ratio)
    b = int(low_b + (high_b - low_b) * ratio)
    return f"#{r:02X}{g:02X}{b:02X}"


def urgency_cell_color(urgency: int | float, min_val: float, max_val: float) -> str:
    if max_val == min_val:
        return URGENCY_HEAT_LOW
    ratio = (urgency - min_val) / (max_val - min_val)
    ratio = max(0.0, min(1.0, ratio))
    return _interpolate_color(URGENCY_HEAT_LOW, URGENCY_HEAT_HIGH, ratio)


def render_batch_queue(batches: list[dict] | None) -> None:
    st.subheader(f"批次队列（{len(batches) if batches else 0}）")
    if not batches:
        st.info("暂无批次")
        return

    sort_options = ["位次", "紧迫度", "状态"]
    current_sort = st.session_state.get(BATCH_SORT_KEY, "位次")
    sort_col, _ = st.columns([1, 3])
    selected_sort = sort_col.selectbox("排序", sort_options, index=sort_options.index(current_sort), key=BATCH_SORT_KEY)

    sorted_batches = list(batches)
    if selected_sort == "紧迫度":
        sorted_batches.sort(key=lambda b: b.get("urgency", 0), reverse=True)
    elif selected_sort == "状态":
        sorted_batches.sort(key=lambda b: b.get("state", ""))
    else:
        sorted_batches.sort(key=lambda b: b.get("queueRank", 0))

    urgencies = [b.get("urgency", 0) for b in sorted_batches]
    min_u = min(urgencies) if urgencies else 0
    max_u = max(urgencies) if urgencies else 0

    header = (
        '<table class="cipm-table"><thead><tr>'
        '<th>批次号</th><th>地块</th><th>位次</th><th>紧迫度</th><th>状态</th>'
        '</tr></thead><tbody>'
    )
    rows_html = []
    for item in sorted_batches:
        urgency = item.get("urgency", 0)
        cell_color = urgency_cell_color(urgency, min_u, max_u)
        state_code = item.get("state", "")
        state_label = BATCH_STATE_LABELS.get(state_code, state_code)
        state_color = BATCH_STATE_COLORS.get(state_code, "#9E9E9E")
        rows_html.append(
            f'<tr>'
            f'<td>{item.get("batchNo", "")}</td>'
            f'<td>{item.get("plotNo", "")}</td>'
            f'<td>{item.get("queueRank", "")}</td>'
            f'<td><span class="urgency-cell" style="background-color:{cell_color}">{urgency}</span></td>'
            f'<td><span class="badge-pill" style="background-color:{state_color}">{state_label}</span></td>'
            f'</tr>'
        )
    footer = '</tbody></table>'
    st.markdown(header + "".join(rows_html) + footer, unsafe_allow_html=True)