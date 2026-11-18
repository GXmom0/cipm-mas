from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from mock.builder import build_dataset
from sdk.contracts.assessment import AssessmentPayload
from sdk.contracts.dispatch import DispatchCommand
from sdk.contracts.envelope import Envelope
from sdk.contracts.prescription import PrescriptionPayload
from sdk.contracts.stress_result import StressResultPayload

TRACE_ID = "0123456789abcdef0123456789abcdef"
TIMESTAMP = "2026-11-13T08:00:00+08:00"


def _normal_stress() -> dict:
    return copy.deepcopy(build_dataset("normal_plot")["stressResults"][0])


def _normal_prescription() -> dict:
    return copy.deepcopy(build_dataset("normal_plot")["prescriptions"][0])


def _conflict_prescription() -> dict:
    return copy.deepcopy(build_dataset("safety_conflict_plot")["prescriptions"][0])


def _dispatch_sample() -> dict:
    return {
        "schemaVersion": "1.0",
        "templateVersion": "TPL-DISPATCH-1.0",
        "workOrderNo": "WO-20261113-0001",
        "plotNo": "PLOT-0912",
        "prescriptionNo": "RX-20261113-0001",
        "prescriptionVersion": 1,
        "batchNo": "BT-20261113-0001",
        "queueRank": 1,
        "urgency": 15.0,
        "zones": [
            {
                "zoneNo": "Z01",
                "zeroApplication": False,
                "doseMlPerMu": 12.0,
                "sprayVolumeLPerMu": 1.6,
                "productCategory": {"aiName": "啶虫脒", "formulation": "乳油"},
            }
        ],
        "flightConstraint": {"altitudeM": 4.5, "speedMps": 4.0},
        "schedule": {"start": "2026-11-14T09:00:00+08:00", "end": "2026-11-14T11:00:00+08:00"},
        "windowCheckRef": {
            "checkNo": "WC-E-20261113-0001",
            "verdict": "pass",
            "thresholdVersion": "XJ-WIN-THR-2026.04",
            "parentCheckNo": "WC-D-20261113-0001",
        },
        "mandatoryNotices": [],
        "mandatoryAck": {"checked": False},
        "operatorConfirm": {"confirmedBy": "manager_li", "confirmedAt": TIMESTAMP},
    }


def _assessment_sample() -> dict:
    return {
        "assessmentNo": "AS-20261113-0001",
        "workOrderNo": "WO-20261113-0001",
        "beforeRef": {"resultNo": "SR-20261113-0001-v1", "resultVersion": 1},
        "afterRef": {"sortieNo": "FL-20261115-002", "resultNo": "SR-20261115-0001-v1", "resultVersion": 1},
        "timeliness": {"completedAt": TIMESTAMP, "assessedAt": TIMESTAMP, "hoursElapsed": 48.0},
        "prescriptionEvidence": {
            "prescriptionNo": "RX-20261113-0001",
            "prescriptionVersion": 1,
            "registryVersion": "XJ-REG-2026.11.01",
            "zoneCount": 12,
            "productCategories": [{"aiName": "啶虫脒", "formulation": "乳油"}],
        },
        "metrics": {"coveragePct": 97.5, "suppressionRate": 0.72, "severeDeviationZones": []},
        "verdictRule": {"verdict": "qualified", "ruleVersion": "ASSESS-RULE-1.0", "ruleExpression": "suppression>=0.6 and coverage>=95"},
        "nextRound": {"recommendedAction": "continue", "note": "保持当前轮换方案"},
    }


def test_envelope_required_fields() -> None:
    envelope = Envelope(traceId=TRACE_ID, timestamp=TIMESTAMP, data={"ok": True})
    assert envelope.code == "OK"
    assert envelope.retryable is False


def test_envelope_trace_id_format() -> None:
    with pytest.raises(ValidationError):
        Envelope(traceId="BAD-ID", timestamp=TIMESTAMP)


def test_envelope_timestamp_timezone() -> None:
    with pytest.raises(ValidationError):
        Envelope(traceId=TRACE_ID, timestamp="2026-11-13T08:00:00Z")


def test_envelope_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        Envelope(traceId=TRACE_ID, timestamp=TIMESTAMP, unknownField=1)


def test_valid_stress_result() -> None:
    payload = StressResultPayload.model_validate(_normal_stress())
    assert payload.resultVersion == 1
    assert payload.recognitionMeta.durationSec <= 600


def test_missing_nir_band_rejected() -> None:
    data = _normal_stress()
    data["orthophoto"]["bands"] = ["RED", "GREEN"]
    with pytest.raises(ValidationError):
        StressResultPayload.model_validate(data)


def test_low_confidence_requires_pending_review() -> None:
    data = _normal_stress()
    data["partitions"][0]["confidence"] = 0.62
    data["partitions"][0]["review"]["status"] = "none_required"
    with pytest.raises(ValidationError):
        StressResultPayload.model_validate(data)


def test_blocked_requires_blocking_partitions() -> None:
    data = _normal_stress()
    data["taskBlock"] = {"status": "blocked_pending_review", "blockingPartitions": [], "reasonCodes": ["LOW_CONFIDENCE"]}
    with pytest.raises(ValidationError):
        StressResultPayload.model_validate(data)


def test_missing_explainability_rejected() -> None:
    data = _normal_stress()
    data["partitions"][0]["explainability"] = {}
    with pytest.raises(ValidationError):
        StressResultPayload.model_validate(data)


def test_valid_prescription() -> None:
    payload = PrescriptionPayload.model_validate(_normal_prescription())
    assert payload.safetyCheck.bufferDays == 13
    for zone in payload.zones:
        assert zone.zeroApplication or zone.doseMlPerMu > 0


def test_triplet_missing_volume_rejected() -> None:
    data = _normal_prescription()
    zone = next(item for item in data["zones"] if not item["zeroApplication"])
    zone["sprayVolumeLPerMu"] = None
    zone["dilutionRatio"] = None
    with pytest.raises(ValidationError):
        PrescriptionPayload.model_validate(data)


def test_volume_conversion_tolerance() -> None:
    data = _normal_prescription()
    zone = next(item for item in data["zones"] if not item["zeroApplication"])
    zone["dilutionRatio"] = 130.0
    with pytest.raises(ValidationError):
        PrescriptionPayload.model_validate(data)

    data = _normal_prescription()
    zone = next(item for item in data["zones"] if not item["zeroApplication"])
    zone["dilutionRatio"] = 132.7
    payload = PrescriptionPayload.model_validate(data)
    assert payload.zones


def test_compound_with_zones_rejected() -> None:
    data = _normal_prescription()
    data["compoundGuard"] = {
        "detected": True,
        "components": [{"category": {"aiName": "啶虫脒", "formulation": "乳油"}, "registryItemNo": "XJ-ACE-0381"}],
        "action": "intercepted_to_expert",
    }
    data["status"] = "refused"
    with pytest.raises(ValidationError):
        PrescriptionPayload.model_validate(data)


def test_buffer_days_consistency() -> None:
    data = _normal_prescription()
    data["safetyCheck"]["bufferDays"] = 10
    with pytest.raises(ValidationError):
        PrescriptionPayload.model_validate(data)


def test_zero_application_with_product_rejected() -> None:
    data = _normal_prescription()
    zero_zone = next(item for item in data["zones"] if item["zeroApplication"])
    zero_zone["product"] = {
        "registryItemNo": "XJ-ACE-0381",
        "registryVersion": "XJ-REG-2026.11.01",
        "category": {"aiName": "啶虫脒", "formulation": "乳油"},
        "registrationNo": "PD20260381",
        "toxicity": "low",
    }
    with pytest.raises(ValidationError):
        PrescriptionPayload.model_validate(data)


def test_refused_prescription_sample() -> None:
    payload = PrescriptionPayload.model_validate(_conflict_prescription())
    assert payload.safetyCheck.conclusion.value == "refused"
    assert payload.safetyCheck.bufferDays == -2
    assert payload.safetyCheck.conflictProduct is not None


def test_batch_fields_must_be_together() -> None:
    data = _dispatch_sample()
    data["batchNo"] = None
    data["queueRank"] = None
    with pytest.raises(ValidationError):
        DispatchCommand.model_validate(data)


def test_mandatory_notice_requires_ack() -> None:
    data = _dispatch_sample()
    data["mandatoryNotices"] = [
        {
            "code": "DRIFT_GUARD_SOUTH",
            "measures": ["提高雾滴粒径", "降低飞行高度", "添加抗漂移助剂", "避开高温时段"],
            "ackRequired": True,
        }
    ]
    with pytest.raises(ValidationError):
        DispatchCommand.model_validate(data)


def test_valid_dispatch_and_idempotency_default() -> None:
    command = DispatchCommand.model_validate(_dispatch_sample())
    assert command.idempotencyKey == command.workOrderNo
    assert command.batchNo == "BT-20261113-0001"


def test_assessment_qualified_rule() -> None:
    payload = AssessmentPayload.model_validate(_assessment_sample())
    assert payload.verdictRule.verdict.value == "qualified"

    data = _assessment_sample()
    data["metrics"]["severeDeviationZones"] = ["Z03"]
    with pytest.raises(ValidationError):
        AssessmentPayload.model_validate(data)