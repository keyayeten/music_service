from redis import Redis

from backend.config.settings import get_settings

_redis_client: Redis | None = None


def create_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


def init_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = create_redis_client()
    return _redis_client


def get_redis_client() -> Redis:
    return init_redis_client()


def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
    _redis_client = None


def check_redis_connection() -> bool:
    return bool(get_redis_client().ping())
