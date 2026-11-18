from __future__ import annotations

from typing import Any

from mock.seed import iso_after
from sdk.contracts.dispatch import DispatchCommand, DispatchReceipt

_RECEIPTS: dict[tuple[str, str], DispatchReceipt] = {}


def dispatch(
    command: DispatchCommand | dict[str, Any], device_no: str = "DEV-XJ-01"
) -> DispatchReceipt:
    parsed = command if isinstance(command, DispatchCommand) else DispatchCommand.model_validate(command)
    key = (parsed.workOrderNo, device_no)
    if key in _RECEIPTS:
        return _RECEIPTS[key]
    accepted = not device_no.endswith("-REJECT")
    receipt = DispatchReceipt(
        receiptNo=f"RC-{parsed.workOrderNo}-{device_no}",
        workOrderNo=parsed.workOrderNo,
        deviceNo=device_no,
        accepted=accepted,
        acceptedAt=iso_after(minutes=1),
        message="已受理" if accepted else "设备拒绝受理：作业窗口或药剂参数不合规",
    )
    _RECEIPTS[key] = receipt
    return receipt


def reset() -> None:
    _RECEIPTS.clear()