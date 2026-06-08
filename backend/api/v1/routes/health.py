from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_app_settings, get_cache_client, get_db_session
from backend.config.settings import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_v1(
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

    return {"status": "ok", "version": "v1", "database": db_status, "redis": redis_status}


@router.post("/cache/ping")
async def cache_ping(
    settings: Settings = Depends(get_app_settings),
    redis_client: Redis = Depends(get_cache_client),
) -> dict[str, str]:
    cache_key = f"{settings.redis_key_prefix}:health:last_ping"
    cache_value = datetime.now(tz=UTC).isoformat()
    await redis_client.setex(cache_key, settings.redis_ttl_seconds, cache_value)
    cached_value = await redis_client.get(cache_key) or ""
    return {"key": cache_key, "value": cached_value}
