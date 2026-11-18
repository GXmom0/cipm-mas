from __future__ import annotations

from typing import Any

from domain.models.enums import (
    BadgeCode,
    BlockStatus,
    CompoundAction,
    DataIntegrity,
    Phenology,
    ReviewStatus,
    SafetyConclusion,
    StressLevel,
    StressType,
)
from mock.scenarios import (
    EXPECTED_VALUES,
    SCENARIO_BY_ID,
    SNAPSHOT_AT,
    PlotSpec,
    ScenarioSpec,
)
from mock.seed import (
    BASELINE_ID,
    BASELINE_VERSION,
    BASE_DATE_ISO,
    DATASET_VERSION,
    REGISTRY_VERSION,
    SEED,
    THRESHOLD_ENTRY_ID,
    THRESHOLD_VERSION,
    WINDOW_THRESHOLD_VERSION,
    iso_after,
    stable_json_dumps,
)
from sdk.contracts.prescription import PrescriptionPayload
from sdk.contracts.stress_result import StressResultPayload

REGISTRY_ITEMS: list[dict[str, Any]] = [
    {
        "registryItemNo": "XJ-ACE-0381",
        "registryVersion": REGISTRY_VERSION,
        "category": {"aiName": "啶虫脒", "formulation": "乳油"},
        "registrationNo": "PD20260381",
        "toxicity": "low",
        "target": "pest_disease",
        "crop": "cotton",
        "safetyIntervalDays": 7,
        "doseRangeMlPerMu": [10.0, 20.0],
        "sprayVolumeRangeLPerMu": [1.2, 2.0],
        "seasonUsageLimit": 3,
        "valid": True,
        "formulationType": "single",
    },
    {
        "registryItemNo": "XJ-IMI-0453",
        "registryVersion": REGISTRY_VERSION,
        "category": {"aiName": "吡虫啉", "formulation": "可湿性粉剂"},
        "registrationNo": "PD20260453",
        "toxicity": "low",
        "target": "pest_disease",
        "crop": "cotton",
        "safetyIntervalDays": 5,
        "doseRangeMlPerMu": [8.0, 16.0],
        "sprayVolumeRangeLPerMu": [1.0, 1.8],
        "seasonUsageLimit": 3,
        "valid": True,
        "formulationType": "single",
    },
    {
        "registryItemNo": "XJ-ABM-0219",
        "registryVersion": REGISTRY_VERSION,
        "category": {"aiName": "阿维菌素", "formulation": "悬浮剂"},
        "registrationNo": "PD20260219",
        "toxicity": "medium",
        "target": "pest_disease",
        "crop": "cotton",
        "safetyIntervalDays": 10,
        "doseRangeMlPerMu": [6.0, 12.0],
        "sprayVolumeRangeLPerMu": [1.0, 1.6],
        "seasonUsageLimit": 2,
        "valid": True,
        "formulationType": "single",
    },
    {
        "registryItemNo": "XJ-MIX-0777",
        "registryVersion": REGISTRY_VERSION,
        "category": {"aiName": "联苯·噻虫嗪", "formulation": "悬浮剂"},
        "registrationNo": "PD20260777",
        "toxicity": "low",
        "target": "pest_disease",
        "crop": "cotton",
        "safetyIntervalDays": 14,
        "doseRangeMlPerMu": [20.0, 40.0],
        "sprayVolumeRangeLPerMu": [1.2, 1.8],
        "seasonUsageLimit": 2,
        "valid": True,
        "formulationType": "mixture_registered",
    },
]


def _split_area(total: float, count: int) -> list[float]:
    base = round(total / count, 2)
    areas = [base for _ in range(count - 1)]
    areas.append(round(total - sum(areas), 2))
    return areas


def _level_for(index: int, stressed: int) -> StressLevel:
    if index >= stressed:
        return StressLevel.NONE
    if index < max(1, stressed // 3):
        return StressLevel.HEAVY
    if index < max(2, stressed * 2 // 3):
        return StressLevel.MEDIUM
    return StressLevel.LIGHT


def _confidence_for(plot: PlotSpec, partition_no: str, index: int) -> float:
    if plot.low_confidence_partition == partition_no:
        return plot.low_confidence_value
    return round(0.88 + (index % 7) * 0.01, 2)


_TARGET_PEST_BY_PLOT: dict[str, str] = {
    "PLOT-0912": "棉蚜",
    "PLOT-0913": "棉铃虫",
    "PLOT-0914": "棉叶螨",
    "PLOT-0915": "红蜘蛛",
    "PLOT-0916": "棉蚜",
}


def _target_pest_for(plot_no: str) -> str:
    return _TARGET_PEST_BY_PLOT.get(plot_no, "")


def _build_partition(plot: PlotSpec, partition_no: str, area_mu: float, index: int) -> dict[str, Any]:
    level = _level_for(index, plot.stressed_partitions)
    confidence = _confidence_for(plot, partition_no, index)
    is_low = plot.low_confidence_partition == partition_no
    stress_type = StressType.UNDETERMINED.value if is_low else StressType.PEST_DISEASE.value
    if level == StressLevel.NONE:
        stress_type = StressType.PEST_DISEASE.value
    needs_review = confidence < 0.7 or stress_type == StressType.UNDETERMINED.value
    if is_low:
        explainability = {
            "ndviDeviation": {
                "value": -0.06,
                "baselineId": BASELINE_ID,
                "baselineVersion": BASELINE_VERSION,
                "method": "分区均值与同物候期健康基线差值",
            }
        }
    else:
        explainability = {
            "pestDensity": {
                "value": round(18.0 + index * 3.5, 1),
                "unit": "头/百株",
                "basis": "黄板计数×百株折算系数 1.15",
            }
        }
    return {
        "partitionNo": partition_no,
        "areaMu": area_mu,
        "geometryRef": f"obs://cipm-geo/{plot.plot_no}/{partition_no}.geojson",
        "stressType": stress_type,
        "stressLevel": level.value,
        "targetPest": _target_pest_for(plot.plot_no),
        "confidence": confidence,
        "explainability": explainability,
        "thresholdRef": {"entryId": THRESHOLD_ENTRY_ID, "version": "v1"},
        "review": {"status": ReviewStatus.PENDING.value if needs_review else ReviewStatus.NONE_REQUIRED.value},
        "frozen": False,
    }


def _build_stress_result(
    plot: PlotSpec, task_no: str, result_no: str, index: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    areas = _split_area(plot.area_mu, plot.partition_count)
    partitions = [
        _build_partition(plot, f"Z{position + 1:02d}", areas[position], position)
        for position in range(plot.partition_count)
    ]
    blocking = [item["partitionNo"] for item in partitions if item["review"]["status"] == "pending"]
    block_status = BlockStatus.BLOCKED_PENDING_REVIEW.value if blocking else BlockStatus.UNBLOCKED.value
    stress_result = {
        "schemaVersion": "1.0",
        "taskNo": task_no,
        "resultNo": result_no,
        "resultVersion": 1,
        "orthophoto": {
            "sortieNo": f"FL-20261113-{index + 20:03d}",
            "readyTime": BASE_DATE_ISO,
            "bands": ["NIR", "RED", "GREEN"],
            "gsdCm": 3.2,
            "cloudPct": 4.0,
            "coverRatio": 1.0,
            "productVersion": f"ortho-2026.11.13-{index + 20:03d}",
        },
        "taskBlock": {
            "status": block_status,
            "blockingPartitions": blocking,
            "reasonCodes": ["LOW_CONFIDENCE"] if blocking else [],
        },
        "partitions": partitions,
        "recognitionMeta": {"durationSec": 240 + index * 7, "dataIntegrity": DataIntegrity.COMPLETE.value},
        "evidence": [
            {"type": "threshold", "refId": THRESHOLD_ENTRY_ID, "version": "v1"},
            {"type": "baseline", "refId": BASELINE_ID, "version": BASELINE_VERSION},
        ],
    }
    return stress_result, partitions


def _build_safety_check(plot: PlotSpec) -> dict[str, Any]:
    alternatives = [
        {
            "registryItemNo": "XJ-IMI-0453",
            "category": {"aiName": "吡虫啉", "formulation": "可湿性粉剂"},
            "safetyIntervalDays": 5,
            "doseRange": [8.0, 16.0],
        }
    ]
    conclusion = plot.expected_conclusion
    payload: dict[str, Any] = {
        "conclusion": conclusion,
        "remainingDays": plot.remaining_days,
        "safetyIntervalDays": plot.safety_interval_days,
        "bufferDays": plot.remaining_days - plot.safety_interval_days,
        "conflictProduct": None,
        "degradeReasons": [],
        "alternatives": alternatives,
    }
    if conclusion == SafetyConclusion.REFUSED.value:
        payload["conflictProduct"] = {
            "registryItemNo": "XJ-ACE-0381",
            "category": {"aiName": "啶虫脒", "formulation": "乳油"},
        }
        payload["alternatives"] = alternatives
    elif conclusion == SafetyConclusion.DEGRADED.value:
        payload["degradeReasons"] = ["BUFFER_LT_3"]
    return payload


def _build_prescription(
    plot: PlotSpec, task_no: str, result_no: str, partitions: list[dict[str, Any]], index: int
) -> dict[str, Any]:
    zones: list[dict[str, Any]] = []
    for partition in partitions:
        if partition["stressLevel"] == StressLevel.NONE.value:
            zones.append(
                {
                    "zoneNo": partition["partitionNo"],
                    "zeroApplication": True,
                    "product": None,
                    "doseMlPerMu": 0,
                    "sprayVolumeLPerMu": 0,
                    "dilutionRatio": None,
                    "safetyIntervalDays": None,
                    "seasonUsageBefore": 0,
                }
            )
            continue
        zones.append(
            {
                "zoneNo": partition["partitionNo"],
                "zeroApplication": False,
                "product": {
                    "registryItemNo": "XJ-ACE-0381",
                    "registryVersion": REGISTRY_VERSION,
                    "category": {"aiName": "啶虫脒", "formulation": "乳油"},
                    "registrationNo": "PD20260381",
                    "toxicity": "low",
                },
                "doseMlPerMu": 12.0,
                "sprayVolumeLPerMu": 1.6,
                "dilutionRatio": None,
                "safetyIntervalDays": plot.safety_interval_days,
                "seasonUsageBefore": 1,
                "volumeCorrection": {
                    "applied": True,
                    "reason": "drip_midpoint",
                    "originalValue": 2.0,
                    "finalValue": 1.6,
                }
                if plot.irrigation.value == "drip"
                else None,
            }
        )
    prescription = {
        "schemaVersion": "1.0",
        "prescriptionNo": f"RX-20261113-{index + 1:04d}",
        "prescriptionVersion": 1,
        "taskNo": task_no,
        "resultNo": result_no,
        "resultVersion": 1,
        "status": plot.expected_status,
        "registrySnapshot": {"version": REGISTRY_VERSION, "syncedAt": BASE_DATE_ISO, "degraded": False},
        "compoundGuard": {"detected": False, "components": [], "action": CompoundAction.NONE.value},
        "safetyCheck": _build_safety_check(plot),
        "windowCheck": {
            "checkNo": f"WC-D-20261113-{index + 1:04d}",
            "conclusion": "pass",
            "thresholdVersion": WINDOW_THRESHOLD_VERSION,
            "parentCheckNo": None,
            "mandatoryNotices": [],
            "candidateWindows": [],
        },
        "zones": zones,
        "evidenceRefs": {
            "thresholdVersion": f"{THRESHOLD_ENTRY_ID}@v1",
            "baselineVersion": BASELINE_VERSION,
            "kbRefs": [{"entryId": "KB-PRESC-HIST-" + plot.plot_no, "version": "v1"}],
            "historyPrescriptionRef": None,
        },
    }
    return prescription


def _stage_for(plot: PlotSpec) -> dict[str, str]:
    if plot.expected_badges == (BadgeCode.BLOCKED,):
        return {"patrol": "阻断待复核", "prescription": "已阻断", "execution": "未开始", "assessment": "未开始"}
    if plot.expected_badges == (BadgeCode.REFUSED,):
        return {"patrol": "已完成", "prescription": "已拒绝", "execution": "不可下发", "assessment": "未开始"}
    if plot.expected_badges == (BadgeCode.RESCHEDULED,):
        return {"patrol": "已完成", "prescription": "已通过", "execution": "待重新排期", "assessment": "未开始"}
    if plot.expected_badges == (BadgeCode.DEGRADED,):
        return {"patrol": "已完成", "prescription": "降级待确认", "execution": "未开始", "assessment": "未开始"}
    return {"patrol": "已完成", "prescription": "待审核", "execution": "未开始", "assessment": "未开始"}


def _build_dashboard(plots: list[PlotSpec]) -> dict[str, Any]:
    plot_views = []
    todos = []
    alerts = []
    for plot in plots:
        stages = _stage_for(plot)
        plot_views.append(
            {
                "plotNo": plot.plot_no,
                "plotName": plot.plot_name,
                "farmNo": "FARM-XJ-HT-01",
                "farmName": "呼图壁棉花示范农场",
                "areaMu": plot.area_mu,
                "stages": stages,
                "badges": [badge.value for badge in plot.expected_badges],
                "updatedAt": SNAPSHOT_AT,
            }
        )
        if BadgeCode.BLOCKED in plot.expected_badges:
            todos.append(
                {
                    "plotNo": plot.plot_no,
                    "type": "review",
                    "text": f"{plot.low_confidence_partition} 置信度 {plot.low_confidence_value}，待人工复核",
                }
            )
            alerts.append({"plotNo": plot.plot_no, "level": "warning", "text": "任务级阻断，处方生成已暂停"})
        if BadgeCode.DEGRADED in plot.expected_badges:
            todos.append({"plotNo": plot.plot_no, "type": "confirm", "text": "降级处方待农技专家确认"})
        if BadgeCode.REFUSED in plot.expected_badges:
            todos.append({"plotNo": plot.plot_no, "type": "replan", "text": "安全间隔冲突，需重新制定处方"})
            alerts.append({"plotNo": plot.plot_no, "level": "error", "text": "距采收 5 天短于安全间隔期 7 天，禁止施药"})
        if BadgeCode.RESCHEDULED in plot.expected_badges:
            todos.append({"plotNo": plot.plot_no, "type": "reschedule", "text": "作业窗口温度不通过，待重新排期"})
            alerts.append({"plotNo": plot.plot_no, "level": "warning", "text": "执行前窗口最低温 11.8℃ 低于 12.5℃ 红线"})
        if not plot.expected_badges:
            todos.append({"plotNo": plot.plot_no, "type": "audit", "text": "处方待农场管理者审核"})
    return {"snapshotAt": SNAPSHOT_AT, "plots": plot_views, "todos": todos, "alerts": alerts}


def _build_calendar(plots: list[PlotSpec]) -> dict[str, Any]:
    calendar: dict[str, Any] = {}
    for plot in plots:
        calendar[plot.plot_no] = {
            "phenology": plot.phenology.value,
            "expectedHarvestDate": plot.harvest_date,
            "remainingDays": plot.remaining_days,
            "windowCloseInDays": max(1, plot.remaining_days // 3),
            "version": "CAL-2026.11",
        }
    return calendar


def build_dataset(scenario_id: str) -> dict[str, Any]:
    spec: ScenarioSpec = SCENARIO_BY_ID[scenario_id]
    stress_results: list[dict[str, Any]] = []
    prescriptions: list[dict[str, Any]] = []
    work_orders: list[dict[str, Any]] = []
    plot_entries: list[dict[str, Any]] = []

    for index, plot in enumerate(spec.plots):
        task_no = f"PT-20261113-{index + 1:04d}"
        result_no = f"SR-20261113-{index + 1:04d}-v1"
        stress_result, partitions = _build_stress_result(plot, task_no, result_no, index)
        StressResultPayload.model_validate(stress_result)
        stress_results.append(stress_result)
        if stress_result["taskBlock"]["status"] != BlockStatus.BLOCKED_PENDING_REVIEW.value:
            prescription = _build_prescription(plot, task_no, result_no, partitions, index)
            PrescriptionPayload.model_validate(prescription)
            prescriptions.append(prescription)
        plot_entries.append(
            {
                "plotNo": plot.plot_no,
                "plotName": plot.plot_name,
                "areaMu": plot.area_mu,
                "region": plot.region.value,
                "irrigation": plot.irrigation.value,
                "phenology": plot.phenology.value,
                "variety": "新陆早 57 号",
                "expectedHarvestDate": plot.harvest_date,
                "owner": "示范农场一组",
            }
        )
        if BadgeCode.RESCHEDULED in plot.expected_badges:
            work_orders.append(
                {
                    "workOrderNo": "WO-20261113-0002",
                    "plotNo": plot.plot_no,
                    "prescriptionNo": prescriptions[-1]["prescriptionNo"],
                    "status": "rescheduled",
                    "windowCheckRef": {
                        "checkNo": "WC-E-20261113-0011",
                        "verdict": "fail",
                        "thresholdVersion": WINDOW_THRESHOLD_VERSION,
                        "parentCheckNo": prescriptions[-1]["windowCheck"]["checkNo"],
                    },
                    "reason": "执行前窗口最低温 11.8℃ 低于 12.5℃，转待重新排期",
                }
            )

    dataset = {
        "schemaVersion": "1.0",
        "scenarioId": spec.scenario_id,
        "scenarioName": spec.scenario_name,
        "description": spec.description,
        "seed": SEED,
        "datasetVersion": DATASET_VERSION,
        "farm": {"farmNo": "FARM-XJ-HT-01", "name": "呼图壁棉花示范农场", "region": "south"},
        "plots": plot_entries,
        "calendar": _build_calendar(list(spec.plots)),
        "registry": REGISTRY_ITEMS,
        "stressResults": stress_results,
        "prescriptions": prescriptions,
        "workOrders": work_orders,
        "dispatchCommands": [],
        "dashboard": _build_dashboard(list(spec.plots)),
        "expected": {plot.plot_no: EXPECTED_VALUES[plot.plot_no] for plot in spec.plots},
    }
    return dataset


def render_dataset(scenario_id: str) -> str:
    return stable_json_dumps(build_dataset(scenario_id))