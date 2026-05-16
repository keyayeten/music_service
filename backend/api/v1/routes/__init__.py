"""Versioned route modules."""

from backend.api.v1.routes.auth import router as auth_router
from backend.api.v1.routes.catalog import router as catalog_router
from backend.api.v1.routes.health import router as health_router
from backend.api.v1.routes.library import router as library_router
from backend.api.v1.routes.profiles import router as profiles_router
from backend.api.v1.routes.social import router as social_router

__all__ = ["health_router", "auth_router", "profiles_router", "catalog_router", "library_router", "social_router"]
