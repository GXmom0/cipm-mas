from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from apps.console.components.stage_badge import badge_label
from apps.console.components.todo_panel import group_todos, todo_count
from apps.console.services import data_source
from mock.loader import dashboard_projection

APP_PATH = Path(__file__).resolve().parents[3] / "apps" / "console" / "app.py"


@pytest.fixture(scope="module", autouse=True)
def prepared_datasets() -> None:
    from mock.cli import write_all

    write_all()


def _run() -> AppTest:
    at = AppTest.from_file(str(APP_PATH), default_timeout=20)
    try:
        at.run()
    except OSError as exc:
        pytest.skip(f"当前执行环境限制本地套接字，跳过仪表盘 AppTest 用例：{exc}")
    return at


def _all_text(at: AppTest) -> str:
    parts: list[str] = []
    for name in ("title", "subheader", "markdown", "caption", "info", "warning", "error", "success"):
        for element in getattr(at, name, []):
            parts.append(str(getattr(element, "value", "")))
    for element in getattr(at, "tabs", []):
        parts.append(str(getattr(element, "label", "")))
    for element in getattr(at, "expander", []):
        parts.append(str(getattr(element, "label", "")))
    return "\n".join(parts)


def test_u01_mock_source(no_network) -> None:
    data_source.get_dashboard.clear()
    data = data_source.get_dashboard(mock=True)
    assert len(data["plots"]) == 5
    assert data["snapshotAt"]


def test_u02_http_failure_degrades(no_network, monkeypatch: pytest.MonkeyPatch) -> None:
    data_source.get_dashboard.clear()

    def _boom(*args, **kwargs):
        raise httpx.ConnectTimeout("连接超时")

    monkeypatch.setattr(data_source.httpx, "get", _boom)
    data = data_source.get_dashboard(mock=False, api_base="http://127.0.0.1:8000")
    assert data["degraded"] is True
    assert data["plots"] == []
    assert data["reason"]
    data_source.get_dashboard.clear()


def test_u03_app_runs_without_exception() -> None:
    at = _run()
    assert not at.exception


def test_u04_stage_progress_in_table() -> None:
    text = _all_text(_run())
    assert "stage-progress-container" in text
    assert "巡" in text
    assert "处" in text
    assert "作" in text
    assert "评" in text


def test_u05_plot_count_in_table() -> None:
    text = _all_text(_run())
    for plot_no in ("PLOT-0912", "PLOT-0913", "PLOT-0914", "PLOT-0915", "PLOT-0916"):
        assert plot_no in text


def test_u06_four_badges_rendered() -> None:
    text = _all_text(_run())
    for label in ("阻断待复核", "已拒绝", "降级待确认", "待重新排期"):
        assert label in text


def test_u07_unknown_badge_fallback() -> None:
    assert badge_label("SOMETHING_NEW") == "未知标识"


def test_u08_todos_grouping_and_count() -> None:
    todos = dashboard_projection()["todos"]
    grouped = group_todos(todos)
    assert todo_count(todos) == len(todos)
    assert sum(len(items) for items in grouped.values()) == len(todos)


def test_u09_empty_batch_state() -> None:
    text = _all_text(_run())
    assert "暂无批次" in text


def test_u10_blocked_view_button_disabled() -> None:
    at = _run()
    blocked_buttons = [button for button in at.button if button.key == "view_prescription_PLOT-0913"]
    assert blocked_buttons
    assert blocked_buttons[0].disabled is True
    assert "待人工复核" in (blocked_buttons[0].help or "")


def test_u11_only_approved_has_dispatch_button() -> None:
    at = _run()
    dispatch_buttons = [button for button in at.button if button.label == "下发作业"]
    assert len(dispatch_buttons) == 1
    assert dispatch_buttons[0].key == "dispatch_PLOT-0916"


def test_u12_no_exemption_entry() -> None:
    text = _all_text(_run())
    assert "豁免" not in text
    assert "跳过校验" not in text


def test_u13_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        data_source,
        "get_dashboard",
        lambda mock=True, api_base="": {
            "plots": [],
            "todos": [],
            "alerts": [],
            "snapshotAt": None,
        },
    )
    at = _run()
    assert not at.exception
    text = _all_text(at)
    assert "暂无巡田记录，可发起首次巡田任务" in text
    assert "快照时间未知" in text


def test_u14_tabs_present() -> None:
    at = _run()
    text = _all_text(at)
    assert "总览" in text
    assert "处方与作业" in text
    assert "待办与批次" in text
    assert "异常与告警" in text
    assert "设置" in text


def test_u15_metric_cards_present() -> None:
    text = _all_text(_run())
    assert "地块总数" in text
    assert "待办总数" in text
    assert "异常总数" in text
    assert "批次总数" in text