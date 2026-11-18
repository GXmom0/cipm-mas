from __future__ import annotations

from typing import Any

from mock.seed import iso_after


def dispatch_sample() -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "templateVersion": "TPL-DISPATCH-1.0",
        "workOrderNo": "WO-20261113-0001",
        "plotNo": "PLOT-0912",
        "prescriptionNo": "RX-20261113-0001",
        "prescriptionVersion": 1,
        "batchNo": "BT-20261113-0001",
        "queueRank": 1,
        "urgency": 15.0,
        "zones": [
            {
                "zoneNo": "Z01",
                "zeroApplication": False,
                "doseMlPerMu": 12.0,
                "sprayVolumeLPerMu": 1.6,
                "productCategory": {"aiName": "啶虫脒", "formulation": "乳油"},
            }
        ],
        "flightConstraint": {"altitudeM": 4.5, "speedMps": 4.0},
        "schedule": {"start": iso_after(days=1, hours=1), "end": iso_after(days=1, hours=3)},
        "windowCheckRef": {
            "checkNo": "WC-E-20261113-0001",
            "verdict": "pass",
            "thresholdVersion": "XJ-WIN-THR-2026.04",
            "parentCheckNo": "WC-D-20261113-0001",
        },
        "mandatoryNotices": [],
        "mandatoryAck": {"checked": False},
        "operatorConfirm": {"confirmedBy": "manager_li", "confirmedAt": iso_after(minutes=30)},
    }