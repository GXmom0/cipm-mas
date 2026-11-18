from __future__ import annotations

import copy
from typing import Any

DOWNGRADE = {
    "heavy": "medium",
    "medium": "light",
    "light": "none",
    "none": "none",
}


def build_recheck(stress_result: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(stress_result)
    for partition in payload["partitions"]:
        partition["stressLevel"] = DOWNGRADE.get(partition["stressLevel"], "none")
        partition["review"] = {"status": "none_required"}
        partition["frozen"] = False
    payload["resultNo"] = f"{stress_result['resultNo']}-recheck"
    payload["resultVersion"] = int(stress_result["resultVersion"]) + 1
    payload["taskBlock"] = {"status": "unblocked", "blockingPartitions": [], "reasonCodes": []}
    return payload