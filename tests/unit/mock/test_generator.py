from __future__ import annotations

import copy
import hashlib
import json

import pytest

from mock.builder import build_dataset
from mock.cli import INDEX_NAME, check_all, write_all
from mock.services import calendar_stub, device_stub, registry_stub, weather_stub
from sdk.contracts.prescription import PrescriptionPayload
from sdk.contracts.stress_result import StressResultPayload
from mock.contract_samples import dispatch_sample

SCENARIOS = ("normal_plot", "low_confidence_plot", "safety_conflict_plot")


@pytest.fixture(scope="module", autouse=True)
def prepared_datasets() -> None:
    write_all()


def test_g01_stable_serialization() -> None:
    from mock.seed import stable_json_dumps

    payload = {"b": 2, "a": [1, 2]}
    assert stable_json_dumps(payload) == stable_json_dumps(payload)
    assert stable_json_dumps(payload) == stable_json_dumps(dict(reversed(list(payload.items()))))


def test_g02_generation_is_reproducible() -> None:
    for scenario in SCENARIOS:
        assert build_dataset(scenario) == build_dataset(scenario)


def test_g03_datasets_pass_contracts() -> None:
    for scenario in SCENARIOS:
        dataset = build_dataset(scenario)
        for stress in dataset["stressResults"]:
            StressResultPayload.model_validate(stress)
        for prescription in dataset["prescriptions"]:
            PrescriptionPayload.model_validate(prescription)


def test_g04_partition_area_sum() -> None:
    for scenario in SCENARIOS:
        dataset = build_dataset(scenario)
        for plot, stress in zip(dataset["plots"], dataset["stressResults"]):
            total = sum(partition["areaMu"] for partition in stress["partitions"])
            assert abs(total - plot["areaMu"]) <= 0.01


def test_g05_zero_application_consistency() -> None:
    for scenario in SCENARIOS:
        dataset = build_dataset(scenario)
        for stress, prescription in zip(dataset["stressResults"], dataset["prescriptions"]):
            zones = {zone["zoneNo"]: zone for zone in prescription["zones"]}
            for partition in stress["partitions"]:
                zone = zones[partition["partitionNo"]]
                if partition["stressLevel"] == "none":
                    assert zone["zeroApplication"] is True
                    assert zone["product"] is None


def test_g06_datasets_exist(datasets_dir) -> None:
    for name in ("normal_plot.json", "low_confidence_plot.json", "safety_conflict_plot.json", INDEX_NAME):
        path = datasets_dir / name
        assert path.exists(), path
        assert json.loads(path.read_text(encoding="utf-8")) is not None


def test_g07_index_hash_matches(datasets_dir) -> None:
    index = json.loads((datasets_dir / INDEX_NAME).read_text(encoding="utf-8"))
    for row in index["scenarios"]:
        text = (datasets_dir / row["fileName"]).read_text(encoding="utf-8").replace("\r\n", "\n")
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == row["fileSha256"]


def test_g08_badges_union(datasets_dir) -> None:
    index = json.loads((datasets_dir / INDEX_NAME).read_text(encoding="utf-8"))
    badges = {badge for row in index["scenarios"] for badge in row["expectedBadges"]}
    assert badges == {"BLOCKED", "DEGRADED", "REFUSED", "RESCHEDULED"}


def test_g17_low_confidence_scenario() -> None:
    dataset = build_dataset("low_confidence_plot")
    partitions = {item["partitionNo"]: item for item in dataset["stressResults"][0]["partitions"]}
    assert partitions["Z03"]["confidence"] == 0.62
    assert partitions["Z03"]["review"]["status"] == "pending"
    assert dataset["stressResults"][0]["taskBlock"]["status"] == "blocked_pending_review"
    assert dataset["prescriptions"] == []


def test_g18_conflict_scenario() -> None:
    dataset = build_dataset("safety_conflict_plot")
    check = dataset["prescriptions"][0]["safetyCheck"]
    assert check["remainingDays"] == 5
    assert check["safetyIntervalDays"] == 7
    assert check["bufferDays"] == -2
    assert check["conclusion"] == "refused"
    assert check["conflictProduct"] is not None
    assert check["alternatives"]


def test_g19_normal_scenario() -> None:
    dataset = build_dataset("normal_plot")
    check = dataset["prescriptions"][0]["safetyCheck"]
    assert check["conclusion"] == "satisfied"
    assert check["bufferDays"] >= 3


def test_g20_degraded_plot() -> None:
    dataset = build_dataset("normal_plot")
    check = dataset["prescriptions"][1]["safetyCheck"]
    assert check["conclusion"] == "degraded"
    assert "BUFFER_LT_3" in check["degradeReasons"]


def test_g14_stubs_contracts(no_network) -> None:
    items = registry_stub.list_items()
    assert items and registry_stub.get_item("XJ-ACE-0381")["safetyIntervalDays"] == 7
    assert calendar_stub.get("PLOT-0912")["remainingDays"] == 20
    assert weather_stub.get_forecast("PLOT-0916")["daily"][0]["minT"] == 11.8
    assert weather_stub.get_forecast("PLOT-0912")["daily"][0]["minT"] >= 12.5


def test_g15_device_stub_idempotent(no_network) -> None:
    device_stub.reset()
    command = dispatch_sample()
    first = device_stub.dispatch(command)
    second = device_stub.dispatch(copy.deepcopy(command))
    assert first == second
    assert first.accepted is True
    rejected = device_stub.dispatch(command, device_no="DEV-XJ-REJECT")
    assert rejected.accepted is False


def test_g16_check_gate_passes() -> None:
    assert check_all() == []