"""Versioned route modules."""

from backend.api.v1.routes.auth import router as auth_router
from backend.api.v1.routes.health import router as health_router

__all__ = ["health_router", "auth_router"]
