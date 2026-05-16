from redis import Redis

from backend.config.settings import get_settings


def create_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url) if settings.redis_url else Redis()
