from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mock.seed import iso_after
from sdk.contracts.assessment import AssessmentPayload

LEVEL_WEIGHT = {"none": 0, "light": 1, "medium": 2, "heavy": 3}
COVERAGE_PASS = 95.0
SUPPRESSION_PASS = 0.6
RULE_VERSION = "ASSESS-RULE-1.0"
RULE_EXPRESSION = "coverage>=95 and suppression>=0.6 and no severe deviation"


@dataclass(frozen=True)
class AssessmentOutcome:
    assessment_no: str
    plot_no: str
    work_order_no: str
    coverage_pct: float
    suppression_rate: float
    verdict: str
    recommended_action: str
    severe_zones: tuple[str, ...]
    deviation_zones: tuple[str, ...]
    payload: dict[str, Any]

    @property
    def qualified(self) -> bool:
        return self.verdict == "qualified"


class AssessmentAgent:
    def assess(
        self,
        plot_no: str,
        before_result: dict[str, Any],
        after_result: dict[str, Any],
        feedback: dict[str, Any],
        prescription: dict[str, Any],
        assessed_at: str | None = None,
    ) -> AssessmentOutcome:
        coverage = float(feedback["coveragePct"])
        before = {item["partitionNo"]: item for item in before_result["partitions"]}
        after = {item["partitionNo"]: item for item in after_result["partitions"]}

        before_total = sum(LEVEL_WEIGHT.get(item["stressLevel"], 0) for item in before.values())
        after_total = sum(LEVEL_WEIGHT.get(item["stressLevel"], 0) for item in after.values())
        if before_total == 0:
            suppression = 0.0
        else:
            suppression = (before_total - after_total) / before_total
        suppression = round(max(-1.0, min(1.0, suppression)), 4)

        severe: list[str] = []
        deviation: list[str] = []
        for zone_no, item in after.items():
            if zone_no not in before:
                continue
            after_weight = LEVEL_WEIGHT.get(item["stressLevel"], 0)
            before_weight = LEVEL_WEIGHT.get(before[zone_no]["stressLevel"], 0)
            if after_weight >= LEVEL_WEIGHT["heavy"]:
                severe.append(zone_no)
            if before_weight > 0 and after_weight >= before_weight:
                deviation.append(zone_no)

        qualified = coverage >= COVERAGE_PASS and suppression >= SUPPRESSION_PASS and not severe
        verdict = "qualified" if qualified else "not_qualified"
        if qualified:
            action = "continue"
        elif severe:
            action = "manual_expert"
        elif coverage < COVERAGE_PASS:
            action = "recheck"
        else:
            action = "recheck"

        assessed = assessed_at or iso_after(days=2)
        completed = feedback["completedAt"]
        hours_elapsed = max(
            0.0,
            (datetime.fromisoformat(assessed) - datetime.fromisoformat(completed)).total_seconds()
            / 3600,
        )
        suffix = plot_no.rsplit("-", 1)[-1]
        categories: dict[tuple[str, str], dict[str, str]] = {}
        for zone in prescription["zones"]:
            product = zone.get("product")
            if product:
                category = product["category"]
                categories[(category["aiName"], category["formulation"])] = {
                    "aiName": category["aiName"],
                    "formulation": category["formulation"],
                }

        payload = {
            "schemaVersion": "1.0",
            "assessmentNo": f"AS-20261113-{suffix}",
            "workOrderNo": feedback["workOrderNo"],
            "beforeRef": {
                "resultNo": before_result["resultNo"],
                "resultVersion": before_result["resultVersion"],
            },
            "afterRef": {
                "sortieNo": after_result["orthophoto"]["sortieNo"],
                "resultNo": after_result["resultNo"],
                "resultVersion": after_result["resultVersion"],
            },
            "timeliness": {
                "completedAt": completed,
                "assessedAt": assessed,
                "hoursElapsed": round(hours_elapsed, 2),
            },
            "prescriptionEvidence": {
                "prescriptionNo": prescription["prescriptionNo"],
                "prescriptionVersion": prescription["prescriptionVersion"],
                "registryVersion": prescription["registrySnapshot"]["version"],
                "zoneCount": len(prescription["zones"]),
                "productCategories": list(categories.values()),
            },
            "metrics": {
                "coveragePct": coverage,
                "suppressionRate": suppression,
                "severeDeviationZones": severe,
                "deviationZones": deviation,
            },
            "verdictRule": {
                "verdict": verdict,
                "ruleVersion": RULE_VERSION,
                "ruleExpression": RULE_EXPRESSION,
            },
            "nextRound": {
                "recommendedAction": action,
                "note": "保持当前方案" if qualified else "建议复核偏差分区并重新评估",
            },
        }
        AssessmentPayload.model_validate(payload)
        return AssessmentOutcome(
            assessment_no=payload["assessmentNo"],
            plot_no=plot_no,
            work_order_no=feedback["workOrderNo"],
            coverage_pct=coverage,
            suppression_rate=suppression,
            verdict=verdict,
            recommended_action=action,
            severe_zones=tuple(severe),
            deviation_zones=tuple(deviation),
            payload=payload,
        )