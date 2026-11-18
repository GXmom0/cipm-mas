from __future__ import annotations

from apps.console.components.todo_panel import classify_todo_priority


def test_priority_high_for_blocked_plot():
    todo = {"type": "audit", "plotNo": "PLOT-0913", "text": "复核阻断"}
    plots = [{"plotNo": "PLOT-0913", "badges": ["BLOCKED"]}]
    assert classify_todo_priority(todo, plots) == "高"


def test_priority_high_for_review_type():
    todo = {"type": "review", "plotNo": "PLOT-0912", "text": "审核处方"}
    plots = [{"plotNo": "PLOT-0912", "badges": []}]
    assert classify_todo_priority(todo, plots) == "高"


def test_priority_high_for_confirm_type():
    todo = {"type": "confirm", "plotNo": "PLOT-0912", "text": "确认处方"}
    plots = [{"plotNo": "PLOT-0912", "badges": []}]
    assert classify_todo_priority(todo, plots) == "高"


def test_priority_medium_for_degraded_plot():
    todo = {"type": "audit", "plotNo": "PLOT-0914", "text": "审核降级"}
    plots = [{"plotNo": "PLOT-0914", "badges": ["DEGRADED"]}]
    assert classify_todo_priority(todo, plots) == "中"


def test_priority_medium_for_rescheduled_plot():
    todo = {"type": "audit", "plotNo": "PLOT-0916", "text": "审核排期"}
    plots = [{"plotNo": "PLOT-0916", "badges": ["RESCHEDULED"]}]
    assert classify_todo_priority(todo, plots) == "中"


def test_priority_medium_for_audit_type():
    todo = {"type": "audit", "plotNo": "PLOT-0912", "text": "审计"}
    plots = [{"plotNo": "PLOT-0912", "badges": []}]
    assert classify_todo_priority(todo, plots) == "中"


def test_priority_low_default():
    todo = {"type": "other", "plotNo": "PLOT-0912", "text": "其他"}
    plots = [{"plotNo": "PLOT-0912", "badges": []}]
    assert classify_todo_priority(todo, plots) == "低"