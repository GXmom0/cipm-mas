from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

SEED = 20261113
TZ_EAST8 = timezone(timedelta(hours=8))
BASE_DATE = datetime(2026, 11, 13, 8, 0, 0, tzinfo=TZ_EAST8)
BASE_DATE_ISO = BASE_DATE.isoformat()
REGISTRY_VERSION = "XJ-REG-2026.11.01"
THRESHOLD_VERSION = "TH-2026.11@v1"
THRESHOLD_ENTRY_ID = "TH-APHID-2026"
BASELINE_ID = "BL-COTTON-FLOWER-2026"
BASELINE_VERSION = "BL-COTTON-FLOWER-2026@v2"
DATASET_VERSION = "2026.11.13"
WINDOW_THRESHOLD_VERSION = "XJ-WIN-THR-2026.04"
TEMPLATE_VERSION = "TPL-DISPATCH-1.0"


def iso_after(days: int = 0, hours: int = 0, minutes: int = 0) -> str:
    return (BASE_DATE + timedelta(days=days, hours=hours, minutes=minutes)).isoformat()


def date_after(days: int) -> str:
    return (BASE_DATE + timedelta(days=days)).date().isoformat()


def stable_json_dumps(payload: object) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    return text.replace("\r\n", "\n") + "\n"