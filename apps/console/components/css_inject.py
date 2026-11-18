from __future__ import annotations

import streamlit as st

from apps.console.theme import (
    CARD_BORDER_RADIUS,
    CARD_BOX_SHADOW,
    CARD_MARGIN_BOTTOM,
    CARD_PADDING,
    NODE_ACTIVE_COLOR,
    NODE_BLOCKED_COLOR,
    NODE_DONE_COLOR,
    NODE_PENDING_COLOR,
    ROW_BLOCKED_BG,
    ROW_DEGRADED_BG,
    URGENCY_HEAT_HIGH,
    URGENCY_HEAT_LOW,
)


def inject_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        /* 卡片样式增强 */
        .stContainer[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: {CARD_BORDER_RADIUS};
            box-shadow: {CARD_BOX_SHADOW};
            padding: {CARD_PADDING};
            margin-bottom: {CARD_MARGIN_BOTTOM};
        }}

        /* 四阶段进度条 */
        .stage-progress-container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
            padding: 4px 0;
        }}
        .stage-node {{
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            color: #FFFFFF;
            font-weight: bold;
            flex-shrink: 0;
        }}
        .stage-node.node-done {{
            background-color: {NODE_DONE_COLOR};
        }}
        .stage-node.node-active {{
            background-color: {NODE_ACTIVE_COLOR};
        }}
        .stage-node.node-blocked {{
            background-color: {NODE_BLOCKED_COLOR};
        }}
        .stage-node.node-pending {{
            background-color: {NODE_PENDING_COLOR};
        }}
        .stage-connector {{
            flex: 1;
            height: 3px;
            margin: 0 4px;
            background-color: #E0E0E0;
            border-radius: 2px;
        }}
        .stage-connector.connector-done {{
            background-color: {NODE_DONE_COLOR};
        }}
        .stage-connector.connector-active {{
            background-color: {NODE_ACTIVE_COLOR};
        }}
        .stage-connector.connector-blocked {{
            background-color: {NODE_BLOCKED_COLOR};
        }}
        .stage-labels {{
            display: flex;
            justify-content: space-between;
            width: 100%;
            margin-top: 4px;
        }}
        .stage-label {{
            font-size: 11px;
            color: #616161;
            text-align: center;
            flex-shrink: 0;
            width: 28px;
        }}

        /* Badge 胶囊样式增强 */
        .badge-pill {{
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 11px;
            font-weight: 500;
            box-shadow: 0 1px 2px rgba(0,0,0,0.08);
            color: #FFFFFF;
            display: inline-block;
            margin: 2px;
        }}

        /* 表格行高亮 */
        .row-blocked {{
            background-color: {ROW_BLOCKED_BG};
        }}
        .row-degraded {{
            background-color: {ROW_DEGRADED_BG};
        }}

        /* 紧迫度热力标识 */
        .urgency-cell {{
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 500;
            text-align: center;
        }}

        /* 自定义 HTML 表格 */
        .cipm-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .cipm-table th {{
            background-color: #E8F5E9;
            padding: 8px 10px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #2E7D32;
            color: #212121;
        }}
        .cipm-table td {{
            padding: 6px 10px;
            border-bottom: 1px solid #E0E0E0;
            color: #212121;
        }}
        .cipm-table tr:hover {{
            background-color: #F5F5F5;
        }}

        /* 指标卡片 */
        .metric-card {{
            border-radius: {CARD_BORDER_RADIUS};
            box-shadow: {CARD_BOX_SHADOW};
            padding: {CARD_PADDING};
            text-align: center;
        }}
        .metric-card .metric-icon {{
            font-size: 28px;
            margin-bottom: 4px;
        }}
        .metric-card .metric-value {{
            font-size: 24px;
            font-weight: 700;
            color: #212121;
        }}
        .metric-card .metric-label {{
            font-size: 12px;
            color: #757575;
            margin-top: 2px;
        }}

        /* 折叠面板增强 */
        .streamlit-expanderHeader {{
            font-weight: 600;
            font-size: 14px;
        }}

        /* 间距分隔 */
        .section-gap {{
            margin-bottom: 24px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )