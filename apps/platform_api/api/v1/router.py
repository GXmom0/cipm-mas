from fastapi import APIRouter

from apps.platform_api.api.v1.agents import router as agents_router
from apps.platform_api.api.v1.dashboard import router as dashboard_router
from apps.platform_api.api.v1.execution import router as execution_router
from apps.platform_api.api.v1.health import router as health_router

router = APIRouter()
router.include_router(health_router)
router.include_router(dashboard_router)
router.include_router(agents_router)
router.include_router(execution_router)