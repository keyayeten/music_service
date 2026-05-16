from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.deps import get_app_settings, get_cache_client, get_db_session
from backend.config.settings import Settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_v1(
    db_session: Session = Depends(get_db_session),
    redis_client: Redis = Depends(get_cache_client),
) -> dict[str, str]:
    db_status = "ok"
    redis_status = "ok"

    try:
        db_session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        redis_client.ping()
    except Exception:
        redis_status = "error"

    return {"status": "ok", "version": "v1", "database": db_status, "redis": redis_status}


@router.post("/cache/ping")
def cache_ping(
    settings: Settings = Depends(get_app_settings),
    redis_client: Redis = Depends(get_cache_client),
) -> dict[str, str]:
    cache_key = f"{settings.redis_key_prefix}:health:last_ping"
    cache_value = datetime.now(tz=UTC).isoformat()
    redis_client.setex(cache_key, settings.redis_ttl_seconds, cache_value)
    cached_value = redis_client.get(cache_key) or ""
    return {"key": cache_key, "value": cached_value}
