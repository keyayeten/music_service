from fastapi import APIRouter

from backend.api.v1.routes.health import router as health_router
from backend.config.settings import get_settings

settings = get_settings()
router = APIRouter(prefix=settings.api_v1_prefix, tags=["v1"])
router.include_router(health_router)
