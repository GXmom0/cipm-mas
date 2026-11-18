from __future__ import annotations

from domain.models.enums import BadgeCode

PAGE_TITLE = "新疆棉田植保决策多智能体系统 · 仪表盘"

COLUMNS = ["地块", "农场", "面积(亩)", "巡田", "处方", "作业", "评估", "业务标识", "更新时间"]

BADGE_COLORS: dict[str, str] = {
    BadgeCode.BLOCKED.value: "#D32F2F",
    BadgeCode.REFUSED.value: "#B71C1C",
    BadgeCode.DEGRADED.value: "#F57C00",
    BadgeCode.RESCHEDULED.value: "#1976D2",
}

BADGE_LABELS: dict[str, str] = {
    BadgeCode.BLOCKED.value: "阻断待复核",
    BadgeCode.REFUSED.value: "已拒绝",
    BadgeCode.DEGRADED.value: "降级待确认",
    BadgeCode.RESCHEDULED.value: "待重新排期",
}

UNKNOWN_BADGE_LABEL = "未知标识"
CACHE_TTL_SECONDS = 30
ACTION_SECTION_TITLE = "地块操作入口（Mock 演示）"
BLOCKED_BUTTON_HELP = "识别结果待人工复核，处方生成已暂停"
NOT_APPROVED_HINT = "未通过审核，不可下发"
NODE_DONE_COLOR = "#4CAF50"
NODE_ACTIVE_COLOR = "#1976D2"
NODE_BLOCKED_COLOR = "#D32F2F"
NODE_PENDING_COLOR = "#9E9E9E"

ROW_BLOCKED_BG = "#FFEBEE"
ROW_DEGRADED_BG = "#FFF3E0"

CARD_BORDER_RADIUS = "8px"
CARD_PADDING = "16px"
CARD_BOX_SHADOW = "0 2px 4px rgba(0,0,0,0.1)"
CARD_MARGIN_BOTTOM = "16px"

SECTION_GAP = "24px"
CARD_GAP = "16px"

STATUS_BLOCKED = "#D32F2F"
STATUS_DEGRADED = "#F57C00"
STATUS_REFUSED = "#B71C1C"
STATUS_RESCHEDULED = "#1976D2"

BATCH_STATE_COLORS: dict[str, str] = {
    "draft": "#9E9E9E",
    "pending_confirm": "#1976D2",
    "queued": "#4CAF50",
    "executing": "#F57C00",
    "completed": "#2E7D32",
    "cancelled": "#D32F2F",
}

BATCH_STATE_LABELS: dict[str, str] = {
    "draft": "草稿",
    "pending_confirm": "待确认",
    "queued": "已入队",
    "executing": "执行中",
    "completed": "已完成",
    "cancelled": "已取消",
}

URGENCY_HEAT_LOW = "#FFF9C4"
URGENCY_HEAT_HIGH = "#D32F2F"

PRIORITY_HIGH_COLOR = "#D32F2F"
PRIORITY_MEDIUM_COLOR = "#F57C00"
PRIORITY_LOW_COLOR = "#1976D2"

BUFFER_DANGER_COLOR = "#D32F2F"
BUFFER_WARNING_COLOR = "#F57C00"
BUFFER_SAFE_COLOR = "#4CAF50"

TAB_OVERVIEW = "总览"
TAB_PRESCRIPTION = "处方与作业"
TAB_TODO_BATCH = "待办与批次"
TAB_ALERT = "异常与告警"
TAB_SETTINGS = "设置"