from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


from mock.scenarios import ALL_SCENARIOS, SCENARIO_BY_ID

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"


def scenarios_dir() -> Path:
    return DATASETS_DIR


def list_scenarios() -> list[dict[str, Any]]:
    rows = []
    for spec in ALL_SCENARIOS:
        rows.append(
            {
                "scenarioId": spec.scenario_id,
                "scenarioName": spec.scenario_name,
                "fileName": spec.file_name,
                "entryPlotNo": spec.entry_plot_no,
                "expectedBadges": [badge.value for badge in spec.expected_badges],
            }
        )
    return rows


def _dataset_path(scenario_id: str) -> Path:
    if scenario_id not in SCENARIO_BY_ID:
        raise KeyError(f"未知场景：{scenario_id}")
    return DATASETS_DIR / SCENARIO_BY_ID[scenario_id].file_name


def load_scenario(scenario_id: str) -> dict[str, Any]:
    path = _dataset_path(scenario_id)
    if not path.exists():
        raise FileNotFoundError(f"演示数据集不存在：{path}，请先执行 python -m mock.cli --write")
    return json.loads(path.read_text(encoding="utf-8"))


def load_all() -> list[dict[str, Any]]:
    return [load_scenario(spec.scenario_id) for spec in ALL_SCENARIOS]


def plot_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for dataset in load_all():
        for plot in dataset["plots"]:
            index[plot["plotNo"]] = {
                "scenarioId": dataset["scenarioId"],
                "plot": copy.deepcopy(plot),
                "calendar": copy.deepcopy(dataset["calendar"].get(plot["plotNo"], {})),
            }
    return index


def plot_bundle(plot_no: str) -> dict[str, Any]:
    for dataset in load_all():
        for index, plot in enumerate(dataset["plots"]):
            if plot["plotNo"] != plot_no:
                continue
            stress = dataset["stressResults"][index] if index < len(dataset["stressResults"]) else None
            prescription = None
            if stress is not None:
                for item in dataset["prescriptions"]:
                    if item.get("resultNo") == stress.get("resultNo"):
                        prescription = item
                        break
            work_order = next(
                (item for item in dataset["workOrders"] if item.get("plotNo") == plot_no),
                None,
            )
            return copy.deepcopy(
                {
                    "scenarioId": dataset["scenarioId"],
                    "plot": plot,
                    "calendar": dataset["calendar"].get(plot_no, {}),
                    "stressResult": stress,
                    "prescription": prescription,
                    "workOrder": work_order,
                    "registry": dataset["registry"],
                }
            )
    raise KeyError(f"未找到地块：{plot_no}")


def dashboard_projection(farm_no: str | None = None) -> dict[str, Any]:
    plots: list[dict[str, Any]] = []
    todos: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    snapshot_at = ""
    for dataset in load_all():
        dashboard = dataset["dashboard"]
        if farm_no and dataset["farm"]["farmNo"] != farm_no:
            continue
        snapshot_at = snapshot_at or dashboard["snapshotAt"]
        plots.extend(copy.deepcopy(dashboard["plots"]))
        todos.extend(copy.deepcopy(dashboard["todos"]))
        alerts.extend(copy.deepcopy(dashboard["alerts"]))
    return {
        "plots": plots,
        "todos": todos,
        "alerts": alerts,
        "snapshotAt": snapshot_at,
    }