from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

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
        pytest.skip(f"当前执行环境限制本地套接字，跳过仪表盘交互用例：{exc}")
    return at


def _text(at: AppTest) -> str:
    parts: list[str] = []
    for name in (
        "title",
        "subheader",
        "markdown",
        "caption",
        "info",
        "warning",
        "error",
        "success",
    ):
        for element in getattr(at, name, []):
            value = str(getattr(element, "value", ""))
            parts.append(value.replace("**", "").replace("`", ""))
    for element in getattr(at, "tabs", []):
        parts.append(str(getattr(element, "label", "")))
    for element in getattr(at, "expander", []):
        parts.append(str(getattr(element, "label", "")).replace("**", "").replace("`", ""))
    return "\n".join(parts)


def _click(at: AppTest, key: str) -> AppTest:
    button = next((item for item in at.button if item.key == key), None)
    assert button is not None, f"未找到按钮 {key}"
    button.click()
    at.run()
    return at


def test_view_prescription_has_real_feedback() -> None:
    at = _click(_run(), "view_prescription_PLOT-0912")
    assert not at.exception
    text = _text(at)
    assert "处方详情" in text
    assert "PLOT-0912" in text
    assert "啶虫脒" in text or "乳油" in text
    assert "XJ-ACE-0381" in text
    assert "XJ-REG-2026.11.01" in text

    assert "满足" in text
    assert "通过" in text

    assert "剩余采收天数" in text
    assert "20" in text
    assert "安全间隔期" in text
    assert "7" in text
    assert "buffer" in text
    assert "13" in text
    assert "处方状态" in text


def test_dispatch_0916_fails_window_and_reschedules() -> None:
    at = _click(_run(), "dispatch_PLOT-0916")
    assert not at.exception
    text = _text(at)
    assert "下发前作业窗口校验" in text
    assert "PLOT-0916" in text
    assert "作业窗口校验不通过" in text or "不通过" in text
    assert "11.8" in text
    assert "待重新排期" in text
    assert "下发成功" not in text


def test_dispatch_only_for_approved_plot() -> None:
    at = _run()
    dispatch_keys = {item.key for item in at.button if item.label == "下发作业"}
    assert dispatch_keys == {"dispatch_PLOT-0916"}


def test_blocked_plot_view_stays_disabled() -> None:
    at = _run()
    button = next(item for item in at.button if item.key == "view_prescription_PLOT-0913")
    assert button.disabled is True
    assert "待人工复核" in (button.help or "")


def test_no_forbidden_entries_after_click() -> None:
    at = _click(_run(), "dispatch_PLOT-0916")
    text = _text(at)
    for word in ("豁免", "跳过校验", "强制下发"):
        assert word not in text
    assert "当前为 local 演示模式" not in text


@pytest.mark.parametrize(
    "weather",
    [
        {
            "daily": [],
            "hourly": [{"at": "2026-11-13T10:00:00+08:00", "windLevel": 2, "rhPct": 34}],
        },
        {
            "daily": [{"date": "2026-11-13", "minT": 13.6, "avgT": 24.8}],
            "hourly": [],
        },
        {"daily": [], "hourly": []},
    ],
)
def test_dispatch_window_treats_missing_forecast_as_unavailable(
    weather, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.console.components import plot_table
    from mock.loader import plot_bundle

    bundle = plot_bundle("PLOT-0916")
    monkeypatch.setattr(plot_table, "get_forecast", lambda plot_no: weather)
    result = plot_table.evaluate_dispatch_window(bundle)
    assert result.passed is False
    assert result.conclusion == "fail"
    assert "数据不可用" in result.violations[0]
    assert result.message == "作业窗口校验不通过，转待重新排期"