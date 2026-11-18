from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from agents.execution.window_guard import evaluate_for_plot
from mock.loader import plot_bundle
from mock.seed import iso_after
from mock.services.device_stub import dispatch as device_dispatch
from sdk.contracts.dispatch import DispatchCommand

TEMPLATE_VERSION = "TPL-DISPATCH-1.0"
WINDOW_THRESHOLD_VERSION = "XJ-WIN-THR-2026.04"
STATUS_DISPATCHED = "dispatched"
STATUS_RESCHEDULED = "rescheduled"
STATUS_REJECTED = "rejected"


@dataclass(frozen=True)
class DispatchOutcome:
    work_order_no: str
    plot_no: str
    status: str
    message: str
    command: dict[str, Any] | None
    receipt: dict[str, Any] | None
    window_conclusion: str | None
    violations: tuple[str, ...] = ()
    notices: tuple[str, ...] = ()

    @property
    def dispatched(self) -> bool:
        return self.status == STATUS_DISPATCHED


class ExecutionAgent:
    def __init__(
        self,
        window_evaluator: Callable[..., Any] = evaluate_for_plot,
        device: Callable[..., Any] = device_dispatch,
    ) -> None:
        self._window_evaluator = window_evaluator
        self._device = device

    def dispatch(
        self,
        plot_no: str,
        prescription: dict[str, Any] | None,
        operator: str = "manager_li",
        device_no: str = "DEV-XJ-01",
        *,
        work_order_no: str | None = None,
    ) -> DispatchOutcome:
        if prescription is None:
            return DispatchOutcome(
                work_order_no="",
                plot_no=plot_no,
                status=STATUS_REJECTED,
                message="该地块没有可执行的处方。",
                command=None,
                receipt=None,
                window_conclusion=None,
            )
        if prescription.get("status") != "approved":
            return DispatchOutcome(
                work_order_no="",
                plot_no=plot_no,
                status=STATUS_REJECTED,
                message="处方未通过审核，不得下发作业。",
                command=None,
                receipt=None,
                window_conclusion=None,
            )

        bundle = plot_bundle(plot_no)
        region = bundle["plot"].get("region", "south")
        window = self._window_evaluator(plot_no, region)
        existing = bundle.get("workOrder") or {}
        override = (work_order_no or "").strip() or None
        resolved_work_order_no = (
            override
            or existing.get("workOrderNo")
            or f"WO-20261113-{plot_no.rsplit('-', 1)[-1]}"
        )

        if not window.passed:
            return DispatchOutcome(
                work_order_no=resolved_work_order_no,
                plot_no=plot_no,
                status=STATUS_RESCHEDULED,
                message=window.message,
                command=None,
                receipt=None,
                window_conclusion=window.conclusion,
                violations=tuple(window.violations),
                notices=tuple(window.notices),
            )

        command = self._build_command(
            plot_no=plot_no,
            work_order_no=resolved_work_order_no,
            prescription=prescription,
            window=window,
            operator=operator,
        )
        DispatchCommand.model_validate(command)
        receipt = self._device(command, device_no)
        receipt_payload = receipt.model_dump() if hasattr(receipt, "model_dump") else dict(receipt)

        if not receipt_payload.get("accepted", False):
            return DispatchOutcome(
                work_order_no=resolved_work_order_no,
                plot_no=plot_no,
                status=STATUS_RESCHEDULED,
                message="设备拒绝受理，作业转待重新排期。",
                command=command,
                receipt=receipt_payload,
                window_conclusion=window.conclusion,
                violations=tuple(window.violations),
                notices=tuple(window.notices),
            )

        return DispatchOutcome(
            work_order_no=resolved_work_order_no,
            plot_no=plot_no,
            status=STATUS_DISPATCHED,
            message="Mock 设备已受理，作业指令进入执行队列。",
            command=command,
            receipt=receipt_payload,
            window_conclusion=window.conclusion,
            notices=tuple(window.notices),
        )

    def _build_command(
        self,
        plot_no: str,
        work_order_no: str,
        prescription: dict[str, Any],
        window: Any,
        operator: str,
    ) -> dict[str, Any]:
        zones = []
        for zone in prescription["zones"]:
            product = zone.get("product")
            zones.append(
                {
                    "zoneNo": zone["zoneNo"],
                    "zeroApplication": bool(zone.get("zeroApplication")),
                    "doseMlPerMu": zone["doseMlPerMu"],
                    "sprayVolumeLPerMu": zone.get("sprayVolumeLPerMu"),
                    "dilutionRatio": zone.get("dilutionRatio"),
                    "productCategory": product["category"] if product else None,
                }
            )

        notices = []
        if window.notices:
            notices.append(
                {
                    "code": "DRIFT_GUARD_SOUTH",
                    "measures": [
                        "提高雾滴粒径",
                        "降低飞行高度",
                        "添加抗漂移助剂",
                        "避开高温时段",
                    ],
                    "ackRequired": True,
                }
            )

        return {
            "schemaVersion": "1.0",
            "templateVersion": TEMPLATE_VERSION,
            "workOrderNo": work_order_no,
            "idempotencyKey": work_order_no,
            "plotNo": plot_no,
            "prescriptionNo": prescription["prescriptionNo"],
            "prescriptionVersion": prescription["prescriptionVersion"],
            "zones": zones,
            "flightConstraint": {"altitudeM": 4.5, "speedMps": 4.0},
            "schedule": {
                "start": iso_after(days=1, hours=1),
                "end": iso_after(days=1, hours=3),
            },
            "windowCheckRef": {
                "checkNo": f"WC-E-20261113-{plot_no.rsplit('-', 1)[-1]}",
                "verdict": window.conclusion,
                "thresholdVersion": WINDOW_THRESHOLD_VERSION,
                "parentCheckNo": prescription["windowCheck"]["checkNo"],
            },
            "mandatoryNotices": notices,
            "mandatoryAck": {
                "checked": bool(notices),
                "checkedBy": operator if notices else None,
                "checkedAt": iso_after(minutes=30) if notices else None,
            },
            "operatorConfirm": {
                "confirmedBy": operator,
                "confirmedAt": iso_after(minutes=30),
            },
        }