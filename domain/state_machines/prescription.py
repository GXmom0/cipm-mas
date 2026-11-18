from __future__ import annotations

from domain.models.enums import PrescriptionStatus
from domain.rules import RuleInputError

ALLOWED_PRESCRIPTION_TRANSITIONS: dict[PrescriptionStatus, frozenset[PrescriptionStatus]] = {
    PrescriptionStatus.DRAFT: frozenset(
        {
            PrescriptionStatus.PENDING_WINDOW,
            PrescriptionStatus.DEGRADED_PENDING_CONFIRM,
            PrescriptionStatus.PENDING_REVIEW,
            PrescriptionStatus.REFUSED,
        }
    ),
    PrescriptionStatus.DEGRADED_PENDING_CONFIRM: frozenset(
        {
            PrescriptionStatus.PENDING_REVIEW,
            PrescriptionStatus.REJECTED,
        }
    ),
    PrescriptionStatus.PENDING_REVIEW: frozenset(
        {
            PrescriptionStatus.APPROVED,
            PrescriptionStatus.REJECTED,
        }
    ),
    PrescriptionStatus.REJECTED: frozenset({PrescriptionStatus.DRAFT}),
    PrescriptionStatus.PENDING_WINDOW: frozenset({PrescriptionStatus.DRAFT}),
    PrescriptionStatus.APPROVED: frozenset(),
    PrescriptionStatus.REFUSED: frozenset(),
}


def allowed_targets(current: PrescriptionStatus) -> frozenset[PrescriptionStatus]:
    return ALLOWED_PRESCRIPTION_TRANSITIONS.get(current, frozenset())


def can_transition(current: PrescriptionStatus, target: PrescriptionStatus) -> bool:
    return target in allowed_targets(current)


def assert_transition(current: PrescriptionStatus, target: PrescriptionStatus) -> None:
    if not can_transition(current, target):
        raise RuleInputError(f"非法处方状态迁移：{current.value} → {target.value}")