from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.console.services import runtime_state


@pytest.fixture
def fake_streamlit(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    fake = SimpleNamespace(session_state={})
    monkeypatch.setattr(runtime_state, "st", fake)
    return fake


@pytest.fixture(scope="module", autouse=True)
def prepared_datasets() -> None:
    from mock.cli import write_all

    write_all()


def test_merge_stages_overrides_without_mutating_source(fake_streamlit) -> None:
    plots = [
        {
            "plotNo": "PLOT-0916",
            "stages": {
                "patrol": "已完成",
                "prescription": "已通过",
                "execution": "未开始",
                "assessment": "未开始",
            },
        }
    ]
    runtime_state.set_stage("PLOT-0916", "execution", "待重新排期")
    merged = runtime_state.merge_stages(plots)
    assert merged[0]["stages"]["execution"] == "待重新排期"
    assert plots[0]["stages"]["execution"] == "未开始"


def test_patrol_baseline_marks_blocked_plot(fake_streamlit) -> None:
    plots = [{"plotNo": "PLOT-0913"}, {"plotNo": "PLOT-0912"}]
    runtime_state.apply_patrol_baseline(plots)
    state = fake_streamlit.session_state[runtime_state.STATE_KEY]
    assert state["PLOT-0913"]["patrol"] == "阻断待复核"
    assert state["PLOT-0913"]["prescription"] == "已阻断"
    assert state["PLOT-0912"]["patrol"] == "已完成"


def test_clear_runtime_state(fake_streamlit) -> None:
    runtime_state.set_stage("PLOT-0916", "execution", "待重新排期")
    runtime_state.clear_runtime_state()
    assert runtime_state.STATE_KEY not in fake_streamlit.session_state


def test_unknown_stage_rejected(fake_streamlit) -> None:
    with pytest.raises(ValueError):
        runtime_state.set_stage("PLOT-0912", "unknown", "x")

def test_clear_filter_state(fake_streamlit) -> None:
    fake_streamlit.session_state["cipm_filter_state_v1"] = {"search": "PLOT"}
    runtime_state.clear_filter_state()
    assert "cipm_filter_state_v1" not in fake_streamlit.session_state


def test_clear_ui_state(fake_streamlit) -> None:
    fake_streamlit.session_state["cipm_filter_state_v1"] = {"search": "PLOT"}
    fake_streamlit.session_state["cipm_active_tab_v1"] = "总览"
    fake_streamlit.session_state["cipm_batch_sort_v1"] = "位次"
    fake_streamlit.session_state[runtime_state.STATE_KEY] = {"PLOT-0916": {"execution": "已下发"}}
    fake_streamlit.session_state[runtime_state.BASELINE_KEY] = True

    runtime_state.clear_ui_state()

    assert "cipm_filter_state_v1" not in fake_streamlit.session_state
    assert "cipm_active_tab_v1" not in fake_streamlit.session_state
    assert "cipm_batch_sort_v1" not in fake_streamlit.session_state
    assert runtime_state.STATE_KEY in fake_streamlit.session_state
    assert runtime_state.BASELINE_KEY in fake_streamlit.session_state