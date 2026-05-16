from __future__ import annotations

import logging

from fastapi import FastAPI
from sqladmin import Admin

from backend.config.settings import Settings, get_settings
from backend.infrastructure.admin.auth import AdminAuth
from backend.infrastructure.admin.views import get_admin_views
from backend.infrastructure.persistence.database import get_engine, init_database

logger = logging.getLogger("backend.admin")


def init_admin(application: FastAPI, settings: Settings | None = None) -> Admin | None:
    config = settings or get_settings()
    if not config.admin_enabled:
        logger.info("Admin panel is disabled (ADMIN_ENABLED=false).")
        return None

    init_database(config)
    auth_backend = AdminAuth(secret_key=config.admin_session_secret)
    admin = Admin(
        application,
        get_engine(),
        authentication_backend=auth_backend,
        base_url=config.admin_base_path.rstrip("/") or "/admin",
    )
    for view_cls in get_admin_views():
        admin.add_view(view_cls)

    logger.info("Admin panel mounted at base_url=%s", config.admin_base_path)
    return admin
