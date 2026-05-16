from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_app_settings, get_cache_client, get_db_session
from backend.config.settings import Settings

router = APIRouter(tags=["system"])


@router.get("/")
def root() -> dict[str, str]:
    return {"message": "music_service is running"}


@router.get("/health")
async def health(
    settings: Settings = Depends(get_app_settings),
    db_session: AsyncSession = Depends(get_db_session),
    redis_client: Redis = Depends(get_cache_client),
) -> dict[str, str]:
    db_status = "ok"
    redis_status = "ok"

    try:
        await db_session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        await redis_client.ping()
    except Exception:
        redis_status = "error"

    return {
        "status": "ok",
        "service": settings.app_name,
        "database": db_status,
        "redis": redis_status,
    }
