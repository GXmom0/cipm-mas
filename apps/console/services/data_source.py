from __future__ import annotations

import httpx
import streamlit as st

from apps.console.theme import CACHE_TTL_SECONDS
from mock.loader import dashboard_projection


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_dashboard(mock: bool = True, api_base: str = "") -> dict:
    if mock:
        return dashboard_projection()
    try:
        response = httpx.get(f"{api_base.rstrip('/')}/api/v1/dashboard", timeout=3.0)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        data["degraded"] = False
        return data
    except Exception as exc:
        return {
            "degraded": True,
            "plots": [],
            "todos": [],
            "alerts": [],
            "snapshotAt": None,
            "reason": str(exc),
        }