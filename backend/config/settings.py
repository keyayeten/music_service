from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    app_name: str
    docs_enabled: bool
    openapi_url: str | None
    swagger_docs_url: str | None
    redoc_url: str | None
    database_url: str
    redis_url: str
    api_v1_prefix: str
    db_echo: bool
    db_pool_size: int
    db_max_overflow: int
    db_pool_timeout: int
    redis_key_prefix: str
    redis_ttl_seconds: int
    redis_ttl_catalog_reads_seconds: int
    redis_ttl_public_playlist_reads_seconds: int
    jwt_secret: str
    jwt_algorithm: str
    jwt_access_ttl_minutes: int
    jwt_refresh_ttl_minutes: int
    log_level: str


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_optional_str(name: str, default: str | None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip()
    return normalized or None


def _get_log_level(name: str, default: str) -> str:
    allowed_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
    value = os.getenv(name, default).strip().upper()
    if value in allowed_levels:
        return value
    return default


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "music_service"),
        docs_enabled=_get_bool("DOCS_ENABLED", True),
        openapi_url=_get_optional_str("OPENAPI_URL", "/openapi.json"),
        swagger_docs_url=_get_optional_str("SWAGGER_DOCS_URL", "/docs"),
        redoc_url=_get_optional_str("REDOC_URL", "/redoc"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://music_user:music_password@localhost:5432/music_service",
        ),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
        db_echo=_get_bool("DB_ECHO", False),
        db_pool_size=_get_int("DB_POOL_SIZE", 5),
        db_max_overflow=_get_int("DB_MAX_OVERFLOW", 10),
        db_pool_timeout=_get_int("DB_POOL_TIMEOUT", 30),
        redis_key_prefix=os.getenv("REDIS_KEY_PREFIX", "music_service"),
        redis_ttl_seconds=_get_int("REDIS_TTL_SECONDS", 60),
        redis_ttl_catalog_reads_seconds=_get_int(
            "REDIS_TTL_CATALOG_READS_SECONDS",
            _get_int("REDIS_TTL_SECONDS", 60),
        ),
        redis_ttl_public_playlist_reads_seconds=_get_int(
            "REDIS_TTL_PUBLIC_PLAYLIST_READS_SECONDS",
            _get_int("REDIS_TTL_SECONDS", 60),
        ),
        jwt_secret=os.getenv("JWT_SECRET", "change-me-in-production"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_access_ttl_minutes=_get_int("JWT_ACCESS_TTL_MINUTES", 15),
        jwt_refresh_ttl_minutes=_get_int("JWT_REFRESH_TTL_MINUTES", 43200),
        log_level=_get_log_level("LOG_LEVEL", "INFO"),
    )
