from fastapi import APIRouter

from backend.api.v1.routes.auth import router as auth_router
from backend.api.v1.routes.health import router as health_router
from backend.api.v1.routes.profiles import router as profiles_router
from backend.config.settings import get_settings

settings = get_settings()
router = APIRouter(prefix=settings.api_v1_prefix, tags=["v1"])
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(profiles_router)
