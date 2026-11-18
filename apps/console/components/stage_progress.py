from __future__ import annotations

STAGE_ORDER: tuple[str, ...] = ("patrol", "prescription", "execution", "assessment")
STAGE_LABELS: dict[str, str] = {
    "patrol": "巡田",
    "prescription": "处方",
    "execution": "作业",
    "assessment": "评估",
}

NODE_COLOR_MAP: dict[str, str] = {
    "已完成": "node-done",
    "已通过": "node-done",
    "已下发": "node-done",
    "达标": "node-done",
    "识别中": "node-active",
    "待审核": "node-active",
    "待作业窗口": "node-active",
    "待下发": "node-active",
    "待评估": "node-active",
    "草稿": "node-active",
    "待接入数据": "node-active",
    "阻断待复核": "node-blocked",
    "已阻断": "node-blocked",
    "已驳回": "node-blocked",
    "已拒绝": "node-blocked",
    "不可下发": "node-blocked",
    "数据接入失败": "node-blocked",
    "未开始": "node-pending",
}


def classify_stage_status(status: str) -> str:
    return NODE_COLOR_MAP.get(status, "node-pending")


def render_stage_progress(stages: dict[str, str]) -> str:
    nodes_html = []
    labels_html = []
    for i, stage_key in enumerate(STAGE_ORDER):
        status = stages.get(stage_key, "未开始")
        color_class = classify_stage_status(status)
        stage_label = STAGE_LABELS[stage_key]
        nodes_html.append(f'<div class="stage-node {color_class}">{stage_label[0]}</div>')
        labels_html.append(f'<div class="stage-label">{stage_label}</div>')
        if i < len(STAGE_ORDER) - 1:
            next_status = stages.get(STAGE_ORDER[i + 1], "未开始")
            next_class = classify_stage_status(next_status)
            connector_class = "connector-done" if color_class == "node-done" else ""
            if color_class == "node-blocked":
                connector_class = "connector-blocked"
            elif color_class == "node-active":
                connector_class = "connector-active"
            nodes_html.append(f'<div class="stage-connector {connector_class}"></div>')

    return (
        '<div class="stage-progress-container">'
        + "".join(nodes_html)
        + '</div><div class="stage-labels">'
        + "".join(labels_html)
        + '</div>'
    )