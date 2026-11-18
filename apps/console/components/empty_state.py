from __future__ import annotations

import streamlit as st

EMPTY_MESSAGE = "暂无巡田记录，可发起首次巡田任务"


def render_empty_state() -> None:
    st.info(EMPTY_MESSAGE)