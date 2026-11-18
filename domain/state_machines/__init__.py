from __future__ import annotations

from domain.state_machines.prescription import (
    ALLOWED_PRESCRIPTION_TRANSITIONS,
    assert_transition as assert_prescription_transition,
    can_transition as can_prescription_transition,
)
from domain.state_machines.work_order import (
    ALLOWED_WORK_ORDER_TRANSITIONS,
    assert_transition as assert_work_order_transition,
    can_transition as can_work_order_transition,
)

__all__ = [
    "ALLOWED_PRESCRIPTION_TRANSITIONS",
    "ALLOWED_WORK_ORDER_TRANSITIONS",
    "assert_prescription_transition",
    "assert_work_order_transition",
    "can_prescription_transition",
    "can_work_order_transition",
]