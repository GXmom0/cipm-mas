from __future__ import annotations

from domain.models.enums import PrescriptionStatus

ALLOWED_TRANSITIONS: dict[PrescriptionStatus, frozenset[PrescriptionStatus]] = {
    PrescriptionStatus.DRAFT: frozenset(
        {
            PrescriptionStatus.PENDING_WINDOW,
            PrescriptionStatus.REFUSED,
            PrescriptionStatus.DEGRADED_PENDING_CONFIRM,
            PrescriptionStatus.PENDING_REVIEW,
        }
    ),
    PrescriptionStatus.PENDING_WINDOW: frozenset({PrescriptionStatus.DRAFT}),
    PrescriptionStatus.DEGRADED_PENDING_CONFIRM: frozenset(
        {PrescriptionStatus.PENDING_REVIEW, PrescriptionStatus.REJECTED}
    ),
    PrescriptionStatus.PENDING_REVIEW: frozenset(
        {PrescriptionStatus.APPROVED, PrescriptionStatus.REJECTED}
    ),
    PrescriptionStatus.REJECTED: frozenset({PrescriptionStatus.DRAFT}),
    PrescriptionStatus.APPROVED: frozenset(),
    PrescriptionStatus.REFUSED: frozenset(),
}

TERMINAL_STATES = frozenset({PrescriptionStatus.APPROVED, PrescriptionStatus.REFUSED})


class IllegalTransition(ValueError):
    def __init__(self, from_status: PrescriptionStatus, to_status: PrescriptionStatus) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"非法处方状态迁移：{from_status.value} → {to_status.value}")


def can_transition(from_status: PrescriptionStatus, to_status: PrescriptionStatus) -> bool:
    return to_status in ALLOWED_TRANSITIONS.get(from_status, frozenset())


def assert_transition(from_status: PrescriptionStatus, to_status: PrescriptionStatus) -> None:
    if not can_transition(from_status, to_status):
        raise IllegalTransition(from_status, to_status)