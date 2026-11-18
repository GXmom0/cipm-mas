from __future__ import annotations

import pytest

from domain.models.enums import PrescriptionStatus as PS
from domain.models.enums import WorkOrderStatus as WS
from domain.rules import RuleInputError
from domain.state_machines import prescription as rx
from domain.state_machines import work_order as wo


@pytest.mark.parametrize(
    "current,target",
    [
        (PS.DRAFT, PS.PENDING_WINDOW),
        (PS.DRAFT, PS.REFUSED),
        (PS.DRAFT, PS.DEGRADED_PENDING_CONFIRM),
        (PS.DRAFT, PS.PENDING_REVIEW),
        (PS.DEGRADED_PENDING_CONFIRM, PS.PENDING_REVIEW),
        (PS.DEGRADED_PENDING_CONFIRM, PS.REJECTED),
        (PS.PENDING_REVIEW, PS.APPROVED),
        (PS.PENDING_REVIEW, PS.REJECTED),
        (PS.REJECTED, PS.DRAFT),
        (PS.PENDING_WINDOW, PS.DRAFT),
    ],
)
def test_prescription_allowed(current: PS, target: PS) -> None:
    assert rx.can_transition(current, target)
    rx.assert_transition(current, target)


@pytest.mark.parametrize(
    "current,target",
    [
        (PS.DRAFT, PS.APPROVED),
        (PS.APPROVED, PS.DRAFT),
        (PS.REFUSED, PS.DRAFT),
        (PS.PENDING_REVIEW, PS.DRAFT),
        (PS.REJECTED, PS.APPROVED),
    ],
)
def test_prescription_forbidden(current: PS, target: PS) -> None:
    assert not rx.can_transition(current, target)
    with pytest.raises(RuleInputError):
        rx.assert_transition(current, target)


@pytest.mark.parametrize(
    "current,target",
    [
        (WS.PENDING_SCHEDULE, WS.PENDING_DISPATCH),
        (WS.PENDING_SCHEDULE, WS.RESCHEDULED),
        (WS.PENDING_DISPATCH, WS.DISPATCHED),
        (WS.PENDING_DISPATCH, WS.RESCHEDULED),
        (WS.DISPATCHED, WS.EXECUTING),
        (WS.DISPATCHED, WS.ABORTED),
        (WS.EXECUTING, WS.COMPLETED),
        (WS.EXECUTING, WS.ABORTED),
        (WS.RESCHEDULED, WS.PENDING_DISPATCH),
        (WS.RESCHEDULED, WS.PENDING_SCHEDULE),
    ],
)
def test_work_order_allowed(current: WS, target: WS) -> None:
    assert wo.can_transition(current, target)
    wo.assert_transition(current, target)


@pytest.mark.parametrize(
    "current,target",
    [
        (WS.EXECUTING, WS.PENDING_DISPATCH),
        (WS.COMPLETED, WS.EXECUTING),
        (WS.ABORTED, WS.EXECUTING),
        (WS.RESCHEDULED, WS.DISPATCHED),
    ],
)
def test_work_order_forbidden(current: WS, target: WS) -> None:
    assert not wo.can_transition(current, target)
    with pytest.raises(RuleInputError):
        wo.assert_transition(current, target)