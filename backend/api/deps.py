from collections.abc import Generator

from redis import Redis
from sqlalchemy.orm import Session

from backend.config.settings import Settings, get_settings
from backend.infrastructure.cache.redis_client import get_redis_client
from backend.infrastructure.persistence.database import get_session


def get_db_session() -> Generator[Session, None, None]:
    yield from get_session()


def get_app_settings() -> Settings:
    return get_settings()


def get_cache_client() -> Redis:
    return get_redis_client()
