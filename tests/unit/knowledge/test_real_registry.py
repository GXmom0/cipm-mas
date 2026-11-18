from __future__ import annotations

from knowledge import print_registry_sources
from knowledge.registry_loader import load_real_registry, load_registry


def test_real_registry_placeholder_count() -> None:
    assert len(load_real_registry()) == 11


def test_real_registry_required_fields() -> None:
    for item in load_real_registry():
        assert item["registryItemNo"]
        assert item["registrationNo"]
        assert item["category"]["aiName"]
        assert item["category"]["formulation"]
        assert item["target"]
        assert item["toxicity"]
        assert item["doseUnit"] in ("ml/mu", "g/mu")
        assert item["source"]


def test_real_registry_no_fabricated_registration() -> None:
    for item in load_real_registry():
        assert item["registrationNo"]
        assert item["registrationNo"] != "PD2026XXXX"


def test_real_registry_ranges_valid() -> None:
    for item in load_real_registry():
        low, high = item["doseRangeMlPerMu"]
        assert low <= high
        vlow, vhigh = item["sprayVolumeRangeLPerMu"]
        assert vlow <= vhigh
        assert item["safetyIntervalDays"] >= 0


def test_default_mode_is_mock(monkeypatch) -> None:
    monkeypatch.delenv("CIPM_REGISTRY_SOURCE", raising=False)
    items = load_registry()
    assert len(items) == 4
    assert any(i["registryItemNo"] == "XJ-ACE-0381" for i in items)


def test_real_mode(monkeypatch) -> None:
    monkeypatch.setenv("CIPM_REGISTRY_SOURCE", "real")
    items = load_registry()
    assert len(items) == 11
    for item in items:
        assert item["source"]


def test_print_sources(capsys, monkeypatch) -> None:
    monkeypatch.setenv("CIPM_REGISTRY_SOURCE", "real")
    print_registry_sources.main()
    out = capsys.readouterr().out
    for item in load_real_registry():
        assert item["registrationNo"] in out
        assert item["source"] in out

def test_real_mode_stub_lists_all(monkeypatch) -> None:
    monkeypatch.setenv("CIPM_REGISTRY_SOURCE", "real")
    from mock.services import registry_stub

    items = registry_stub.list_items()
    assert len(items) == 11
    assert all(item["valid"] for item in items)