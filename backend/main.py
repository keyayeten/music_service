from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from backend.api.system.router import router as system_router
from backend.api.v1.router import router as api_v1_router
from backend.config.settings import get_settings
from backend.infrastructure.cache.redis_client import close_redis_client, init_redis_client
from backend.infrastructure.persistence.database import close_database, init_database

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_database(settings)
    init_redis_client()
    try:
        yield
    finally:
        close_redis_client()
        close_database()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.include_router(system_router)
    application.include_router(api_v1_router)
    return application


app = create_app()
