from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from apps.console.theme import NODE_BLOCKED_COLOR, NODE_DONE_COLOR, STATUS_DEGRADED

STRESS_LEVELS: tuple[str, ...] = ("无", "轻度", "中度", "重度")
STRESS_COLORS: dict[str, str] = {
    "无": NODE_DONE_COLOR,
    "轻度": "#FFEB3B",
    "中度": STATUS_DEGRADED,
    "重度": NODE_BLOCKED_COLOR,
}


def build_stress_data(plots: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {level: 0 for level in STRESS_LEVELS}
    for plot in plots:
        stages = plot.get("stages") or {}
        patrol_status = stages.get("patrol", "")
        if "阻断" in patrol_status:
            counts["重度"] += 1
        elif "降级" in patrol_status:
            counts["中度"] += 1
        elif patrol_status == "已完成":
            counts["无"] += 1
        else:
            counts["轻度"] += 1
    return counts


def render_stress_chart(plots: list[dict]) -> None:
    data = build_stress_data(plots)
    levels = list(data.keys())
    values = list(data.values())
    all_none = all(count == 0 for level, count in data.items() if level != "无")

    df = pd.DataFrame({"胁迫等级": levels, "地块数量": values})
    domain = levels
    color_range = [STRESS_COLORS[level] for level in levels]

    bars = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("胁迫等级:N", sort=domain, title="胁迫等级"),
            y=alt.Y("地块数量:Q", title="地块数量"),
            color=alt.Color(
                "胁迫等级:N",
                scale=alt.Scale(domain=domain, range=color_range),
                legend=None,
            ),
            tooltip=["胁迫等级", "地块数量"],
        )
    )

    text = bars.mark_text(dy=-8, fontSize=14, fontWeight="bold").encode(
        text="地块数量:Q",
        color=alt.value("#424242"),
    )

    chart = (bars + text).properties(height=300, title="胁迫等级分布")

    if all_none:
        annotation = (
            alt.Chart(pd.DataFrame({"x": [1.5], "y": [max(values) / 2 if max(values) else 1], "t": ["全部地块无胁迫"]}))
            .mark_text(fontSize=15, color="#757575")
            .encode(x="x:Q", y="y:Q", text="t:N")
        )
        chart = chart + annotation

    st.altair_chart(chart, width="stretch")