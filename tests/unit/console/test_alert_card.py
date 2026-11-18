from __future__ import annotations

from apps.console.components.alert_card import classify_alert_severity


def test_classify_alert_severity_high():
    alert = {"plotNo": "PLOT-0913", "text": "阻断告警"}
    plots = [{"plotNo": "PLOT-0913", "badges": ["BLOCKED"]}]
    assert classify_alert_severity(alert, plots) == "high"


def test_classify_alert_severity_medium():
    alert = {"plotNo": "PLOT-0914", "text": "降级告警"}
    plots = [{"plotNo": "PLOT-0914", "badges": ["DEGRADED"]}]
    assert classify_alert_severity(alert, plots) == "medium"


def test_classify_alert_severity_low():
    alert = {"plotNo": "PLOT-0912", "text": "普通告警"}
    plots = [{"plotNo": "PLOT-0912", "badges": []}]
    assert classify_alert_severity(alert, plots) == "low"


def test_classify_alert_severity_low_no_matching_plot():
    alert = {"plotNo": "PLOT-9999", "text": "未知地块告警"}
    plots = [{"plotNo": "PLOT-0912", "badges": ["BLOCKED"]}]
    assert classify_alert_severity(alert, plots) == "low"