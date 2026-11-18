from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from mock.builder import build_dataset
from mock.loader import DATASETS_DIR
from mock.scenarios import ALL_SCENARIOS
from mock.seed import stable_json_dumps

INDEX_NAME = "index.json"
DEMO_STEPS = [
    "1. 执行 python -m mock.cli --write 生成三份场景数据",
    "2. 执行 CIPM_MOCK=1 python ops/start_dev.py 启动服务",
    "3. 仪表盘按场景切换：正常 / 置信度不足 / 安全间隔冲突",
    "4. 查看阻断、降级、拒绝、待重新排期四类徽标与中文原因",
]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_index(files: dict[str, str]) -> dict[str, Any]:
    scenarios = []
    for spec in ALL_SCENARIOS:
        dataset = build_dataset(spec.scenario_id)
        scenarios.append(
            {
                "scenarioId": spec.scenario_id,
                "scenarioName": spec.scenario_name,
                "fileName": spec.file_name,
                "entryPlotNo": spec.entry_plot_no,
                "expectedBadges": [badge.value for badge in spec.expected_badges],
                "expectedRuleConclusion": {
                    plot.plot_no: dataset["expected"][plot.plot_no] for plot in spec.plots
                },
                "fileSha256": _sha256(files[spec.file_name]),
            }
        )
    return {
        "datasetVersion": "2026.11.13",
        "generatedBy": "python -m mock.cli --write",
        "scenarios": scenarios,
        "demoSteps": DEMO_STEPS,
    }


def write_all(target: Path = DATASETS_DIR) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    written: list[Path] = []
    for spec in ALL_SCENARIOS:
        text = stable_json_dumps(build_dataset(spec.scenario_id))
        files[spec.file_name] = text
        path = target / spec.file_name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    index_text = stable_json_dumps(build_index(files))
    index_path = target / INDEX_NAME
    index_path.write_text(index_text, encoding="utf-8", newline="\n")
    written.append(index_path)
    return written


def check_all(target: Path = DATASETS_DIR) -> list[str]:
    problems: list[str] = []
    files: dict[str, str] = {}
    for spec in ALL_SCENARIOS:
        path = target / spec.file_name
        if not path.exists():
            problems.append(f"{spec.file_name}: 文件缺失")
            continue
        expected = stable_json_dumps(build_dataset(spec.scenario_id))
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if current != expected:
            problems.append(f"{spec.file_name}: 内容与构造器不一致")
        files[spec.file_name] = current
    index_path = target / INDEX_NAME
    if not index_path.exists():
        problems.append(f"{INDEX_NAME}: 文件缺失")
        return problems
    expected_index = stable_json_dumps(build_index(files))
    current_index = index_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if current_index != expected_index:
        try:
            current_data = json.loads(current_index)
            expected_data = json.loads(expected_index)
            for row_expected, row_current in zip(expected_data["scenarios"], current_data["scenarios"]):
                if row_expected.get("fileSha256") != row_current.get("fileSha256"):
                    problems.append(f"{INDEX_NAME}: {row_expected['scenarioId']} 哈希不一致")
        except json.JSONDecodeError:
            problems.append(f"{INDEX_NAME}: 内容与构造器不一致")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mock 数据集生成与可重现检查")
    parser.add_argument(
        "--scenario",
        default="all",
        choices=[spec.scenario_id for spec in ALL_SCENARIOS] + ["all"],
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="重新生成数据集")
    group.add_argument("--check", action="store_true", help="检查数据集与代码是否一致")
    args = parser.parse_args(argv)

    if args.scenario != "all":
        from mock.builder import render_dataset
        from mock.scenarios import SCENARIO_BY_ID

        spec = SCENARIO_BY_ID[args.scenario]
        path = DATASETS_DIR / spec.file_name
        expected = render_dataset(spec.scenario_id)
        if args.write:
            DATASETS_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8", newline="\n")
            print(f"已生成 {path}")
            return 0
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else ""
        if current != expected:
            print(f"{spec.file_name}: 内容不一致", file=sys.stderr)
            return 2
        print(f"{spec.file_name}: 一致")
        return 0

    if args.write:
        for path in write_all():
            print(f"已生成 {path.name}")
        return 0
    problems = check_all()
    if problems:
        for item in problems:
            print(f"数据集漂移：{item}", file=sys.stderr)
        return 2
    print("数据集一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())