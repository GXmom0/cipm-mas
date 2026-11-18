from __future__ import annotations

from apps.console.components.stage_progress import (
    classify_stage_status,
    render_stage_progress,
    STAGE_ORDER,
)


def test_classify_stage_status_done():
    assert classify_stage_status("已完成") == "node-done"
    assert classify_stage_status("已通过") == "node-done"
    assert classify_stage_status("已下发") == "node-done"
    assert classify_stage_status("达标") == "node-done"


def test_classify_stage_status_blocked():
    assert classify_stage_status("阻断待复核") == "node-blocked"
    assert classify_stage_status("已阻断") == "node-blocked"
    assert classify_stage_status("已拒绝") == "node-blocked"
    assert classify_stage_status("不可下发") == "node-blocked"


def test_classify_stage_status_active():
    assert classify_stage_status("待审核") == "node-active"
    assert classify_stage_status("待下发") == "node-active"
    assert classify_stage_status("待评估") == "node-active"


def test_classify_stage_status_unknown_defaults_to_pending():
    assert classify_stage_status("未知状态") == "node-pending"
    assert classify_stage_status("未开始") == "node-pending"


def test_render_stage_progress_returns_html_with_four_nodes():
    stages = {
        "patrol": "已完成",
        "prescription": "已阻断",
        "execution": "未开始",
        "assessment": "未开始",
    }
    html = render_stage_progress(stages)
    assert "stage-progress-container" in html
    assert "stage-labels" in html
    assert "巡" in html
    assert "处" in html
    assert "作" in html
    assert "评" in html
    assert "node-done" in html
    assert "node-blocked" in html
    assert "node-pending" in html