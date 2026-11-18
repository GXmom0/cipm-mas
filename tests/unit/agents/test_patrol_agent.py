from __future__ import annotations

import pytest

from agents.patrol.agent import BLOCKED, UNBLOCKED, PatrolAgent


@pytest.fixture(scope="module", autouse=True)
def prepared_datasets() -> None:
    from mock.cli import write_all

    write_all()


def test_normal_plot_is_unblocked_and_explainable() -> None:
    result = PatrolAgent().inspect("PLOT-0912")
    assert result.block_status == UNBLOCKED
    assert result.blocking_partitions == ()
    assert len(result.partitions) == 12
    for partition in result.partitions:
        assert partition.stress_level in {"none", "light", "medium", "heavy"}
        assert partition.indicators, partition.partition_no
    assert result.payload["taskBlock"]["status"] == UNBLOCKED


def test_low_confidence_partition_blocks_downstream() -> None:
    result = PatrolAgent().inspect("PLOT-0913")
    assert result.block_status == BLOCKED
    assert result.blocked is True
    assert result.blocking_partitions == ("Z03",)
    partition = next(item for item in result.partitions if item.partition_no == "Z03")
    assert partition.confidence == 0.62
    assert partition.requires_review is True
    assert partition.indicators
    assert "LOW_CONFIDENCE" in result.reason_codes
    assert result.payload["taskBlock"]["status"] == "blocked_pending_review"
    assert result.payload["taskBlock"]["blockingPartitions"] == ["Z03"]
    z03 = next(item for item in result.payload["partitions"] if item["partitionNo"] == "Z03")
    assert z03["review"]["status"] == "pending"


def test_patrol_outputs_contract_payload() -> None:
    from sdk.contracts.stress_result import StressResultPayload

    result = PatrolAgent().inspect("PLOT-0914")
    StressResultPayload.model_validate(result.payload)
    assert result.payload["resultNo"] == result.result_no
    assert result.payload["resultVersion"] == result.result_version