from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from mock.loader import plot_bundle
from sdk.contracts.stress_result import StressResultPayload

CONFIDENCE_THRESHOLD = 0.7
BLOCKED = "blocked_pending_review"
UNBLOCKED = "unblocked"
REASON_LOW_CONFIDENCE = "LOW_CONFIDENCE"
REASON_MISSING_EXPLAINABILITY = "EXPLAINABILITY_MISSING"


@dataclass(frozen=True)
class PatrolPartition:
    partition_no: str
    stress_level: str
    confidence: float
    indicators: tuple[str, ...]
    ndvi_deviation: float | None
    pest_density: float | None
    requires_review: bool

    @property
    def has_explainability(self) -> bool:
        return bool(self.indicators)


@dataclass(frozen=True)
class PatrolResult:
    plot_no: str
    task_no: str
    result_no: str
    result_version: int
    block_status: str
    blocking_partitions: tuple[str, ...]
    reason_codes: tuple[str, ...]
    partitions: tuple[PatrolPartition, ...]
    payload: dict[str, Any]

    @property
    def blocked(self) -> bool:
        return self.block_status == BLOCKED


class PatrolAgent:
    def inspect(self, plot_no: str) -> PatrolResult:
        bundle = plot_bundle(plot_no)
        stress = bundle.get("stressResult")
        if not stress:
            raise LookupError(f"地块 {plot_no} 缺少巡田识别结果")

        partitions: list[PatrolPartition] = []
        blocking: list[str] = []
        reasons: set[str] = set()

        for raw in stress["partitions"]:
            explainability = raw.get("explainability") or {}
            indicators = tuple(
                name
                for name in ("ndviDeviation", "pestDensity")
                if explainability.get(name) is not None
            )
            ndvi_value = (explainability.get("ndviDeviation") or {}).get("value")
            pest_value = (explainability.get("pestDensity") or {}).get("value")
            low_confidence = float(raw["confidence"]) < CONFIDENCE_THRESHOLD
            missing_explainability = not indicators
            requires_review = low_confidence or missing_explainability
            if low_confidence:
                reasons.add(REASON_LOW_CONFIDENCE)
            if missing_explainability:
                reasons.add(REASON_MISSING_EXPLAINABILITY)
            if requires_review:
                blocking.append(raw["partitionNo"])

            partitions.append(
                PatrolPartition(
                    partition_no=raw["partitionNo"],
                    stress_level=raw["stressLevel"],
                    confidence=float(raw["confidence"]),
                    indicators=indicators,
                    ndvi_deviation=float(ndvi_value) if ndvi_value is not None else None,
                    pest_density=float(pest_value) if pest_value is not None else None,
                    requires_review=requires_review,
                )
            )

        payload = copy.deepcopy(stress)
        payload["taskBlock"] = {
            "status": BLOCKED if blocking else UNBLOCKED,
            "blockingPartitions": blocking,
            "reasonCodes": sorted(reasons),
        }
        if blocking:
            for partition in payload["partitions"]:
                if partition["partitionNo"] in blocking:
                    review = partition.setdefault("review", {})
                    if review.get("status") == "none_required":
                        review["status"] = "pending"
        StressResultPayload.model_validate(payload)

        return PatrolResult(
            plot_no=plot_no,
            task_no=payload["taskNo"],
            result_no=payload["resultNo"],
            result_version=payload["resultVersion"],
            block_status=payload["taskBlock"]["status"],
            blocking_partitions=tuple(blocking),
            reason_codes=tuple(sorted(reasons)),
            partitions=tuple(partitions),
            payload=payload,
        )