import logging

from redis.asyncio import Redis

from backend.config.settings import get_settings

_redis_client: Redis | None = None
logger = logging.getLogger("backend.redis")


def create_redis_client() -> Redis:
    settings = get_settings()
    logger.info("Creating Redis client.")
    return Redis.from_url(settings.redis_url, decode_responses=True)


def init_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = create_redis_client()
    else:
        logger.debug("Redis client already initialized.")
    return _redis_client


def get_redis_client() -> Redis:
    return init_redis_client()


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        logger.info("Closing Redis client.")
        await _redis_client.aclose()
    _redis_client = None


async def check_redis_connection() -> bool:
    is_alive = bool(await get_redis_client().ping())
    if is_alive:
        logger.debug("Redis connection check succeeded.")
    else:
        logger.error("Redis connection check failed.")
    return is_alive
