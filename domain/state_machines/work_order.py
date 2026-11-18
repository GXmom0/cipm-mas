from __future__ import annotations

from domain.models.enums import WorkOrderStatus
from domain.rules import RuleInputError

ALLOWED_WORK_ORDER_TRANSITIONS: dict[WorkOrderStatus, frozenset[WorkOrderStatus]] = {
    WorkOrderStatus.PENDING_SCHEDULE: frozenset(
        {
            WorkOrderStatus.PENDING_DISPATCH,
            WorkOrderStatus.RESCHEDULED,
        }
    ),
    WorkOrderStatus.PENDING_DISPATCH: frozenset(
        {
            WorkOrderStatus.DISPATCHED,
            WorkOrderStatus.RESCHEDULED,
        }
    ),
    WorkOrderStatus.DISPATCHED: frozenset(
        {
            WorkOrderStatus.EXECUTING,
            WorkOrderStatus.ABORTED,
        }
    ),
    WorkOrderStatus.EXECUTING: frozenset(
        {
            WorkOrderStatus.COMPLETED,
            WorkOrderStatus.ABORTED,
        }
    ),
    WorkOrderStatus.RESCHEDULED: frozenset(
        {
            WorkOrderStatus.PENDING_DISPATCH,
            WorkOrderStatus.PENDING_SCHEDULE,
        }
    ),
    WorkOrderStatus.COMPLETED: frozenset(),
    WorkOrderStatus.ABORTED: frozenset(),
}


def allowed_targets(current: WorkOrderStatus) -> frozenset[WorkOrderStatus]:
    return ALLOWED_WORK_ORDER_TRANSITIONS.get(current, frozenset())


def can_transition(current: WorkOrderStatus, target: WorkOrderStatus) -> bool:
    return target in allowed_targets(current)


def assert_transition(current: WorkOrderStatus, target: WorkOrderStatus) -> None:
    if not can_transition(current, target):
        raise RuleInputError(f"非法作业单状态迁移：{current.value} → {target.value}")