from fastapi import APIRouter

from backend.api.v1.routes.auth import router as auth_router
from backend.api.v1.routes.catalog import router as catalog_router
from backend.api.v1.routes.discovery import router as discovery_router
from backend.api.v1.routes.health import router as health_router
from backend.api.v1.routes.library import router as library_router
from backend.api.v1.routes.profiles import router as profiles_router
from backend.api.v1.routes.social import router as social_router
from backend.config.settings import get_settings

settings = get_settings()
router = APIRouter(prefix=settings.api_v1_prefix, tags=["v1"])
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(profiles_router)
router.include_router(catalog_router)
router.include_router(library_router)
router.include_router(social_router)
router.include_router(discovery_router)
