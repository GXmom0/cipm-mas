from __future__ import annotations

from fastapi import Request

from apps.platform_api.core.clock import Clock
from apps.platform_api.repository.audit_repo import AuditRepo
from apps.platform_api.repository.idempotency_repo import IdempotencyRepo
from apps.platform_api.repository.snapshot_repo import SnapshotRepo
from sdk.settings import CipmSettings


def get_settings(request: Request) -> CipmSettings:
    return request.app.state.settings


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


def get_audit_repo(request: Request) -> AuditRepo:
    return request.app.state.audit_repo


def get_snapshot_repo(request: Request) -> SnapshotRepo:
    return request.app.state.snapshot_repo

def get_idempotency_repo(request: Request) -> IdempotencyRepo:
    return request.app.state.idempotency_repo