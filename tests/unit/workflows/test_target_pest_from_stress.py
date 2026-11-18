from __future__ import annotations

import pytest


@pytest.fixture(scope="module", autouse=True)
def prepared_datasets() -> None:
    from mock.cli import write_all

    write_all()


def test_stress_partition_has_target_pest() -> None:
    from mock.loader import plot_bundle

    stress = plot_bundle("PLOT-0912")["stressResult"]
    assert stress["partitions"]
    assert stress["partitions"][0]["targetPest"] == "棉蚜"


def test_build_request_passes_target_pest_from_stress() -> None:
    from workflows.local.runtime_demo import build_request

    request = build_request("normal_plot")
    assert request.target_pest != ""