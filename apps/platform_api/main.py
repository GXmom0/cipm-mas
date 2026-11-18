from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.platform_api.api.v1.router import router
from apps.platform_api.core.clock import Clock, SystemClock
from apps.platform_api.core.handlers import register_exception_handlers
from apps.platform_api.core.trace import TraceMiddleware
from apps.platform_api.repository.audit_repo import AuditRepo
from apps.platform_api.repository.idempotency_repo import IdempotencyRepo
from apps.platform_api.repository.snapshot_repo import SnapshotRepo
from apps.platform_api.version import VERSION
from sdk.settings import CipmSettings


def create_app(settings: CipmSettings | None = None, clock: Clock | None = None) -> FastAPI:
    resolved_settings = settings or CipmSettings.from_env()
    resolved_clock = clock or SystemClock()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        Path(resolved_settings.data_dir).mkdir(parents=True, exist_ok=True)
        Path(resolved_settings.audit_dir).mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(
        title="新疆棉田植保决策多智能体系统",
        version=VERSION,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.clock = resolved_clock
    app.state.audit_repo = AuditRepo(resolved_settings.audit_dir, resolved_clock)
    app.state.snapshot_repo = SnapshotRepo()
    app.state.idempotency_repo = IdempotencyRepo(
        Path(resolved_settings.data_dir) / "idempotency.json",
        resolved_clock,
        ttl_seconds=resolved_settings.idempotency_ttl_seconds,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:8501", "http://localhost:8501"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.add_middleware(TraceMiddleware)
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()