from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel

from sdk.contracts.assessment import AssessmentPayload
from sdk.contracts.dispatch import DispatchCommand
from sdk.contracts.envelope import Envelope
from sdk.contracts.prescription import PrescriptionPayload
from sdk.contracts.stress_result import StressResultPayload

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

MODELS: dict[str, type[BaseModel]] = {
    "envelope": Envelope,
    "stress_result": StressResultPayload,
    "prescription": PrescriptionPayload,
    "dispatch": DispatchCommand,
    "assessment": AssessmentPayload,
}


def stable_json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def render_schema(name: str) -> str:
    return stable_json_dumps(MODELS[name].model_json_schema())


def write_all(target: Path = SCHEMA_DIR) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in MODELS:
        path = target / f"{name}.schema.json"
        path.write_text(render_schema(name), encoding="utf-8", newline="\n")
        written.append(path)
    return written


def check_all(target: Path = SCHEMA_DIR) -> list[str]:
    drift: list[str] = []
    for name in MODELS:
        path = target / f"{name}.schema.json"
        if not path.exists():
            drift.append(f"{name}: 缺少文件 {path}")
            continue
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        expected = render_schema(name)
        if current != expected:
            drift.append(f"{name}: 与模型不一致")
    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="契约 JSON Schema 导出与一致性检查")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="重新导出全部 schema")
    group.add_argument("--check", action="store_true", help="比对磁盘 schema 与模型")
    args = parser.parse_args(argv)

    if args.write:
        for path in write_all():
            print(f"已导出 {path.name}")
        return 0
    drift = check_all()
    if drift:
        print("Schema 漂移：", file=sys.stderr)
        for item in drift:
            print(f"  - {item}", file=sys.stderr)
        return 2
    print("Schema 一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())