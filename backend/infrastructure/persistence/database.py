import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config.settings import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
logger = logging.getLogger("backend.database")


def init_database(settings: Settings | None = None) -> None:
    global _engine, _session_factory
    config = settings or get_settings()
    if _engine is not None:
        logger.debug("Database engine already initialized.")
        return
    logger.info(
        "Initializing database engine with pool_size=%s max_overflow=%s.",
        config.db_pool_size,
        config.db_max_overflow,
    )
    _engine = create_async_engine(
        config.database_url,
        echo=config.db_echo,
        pool_pre_ping=True,
        pool_size=config.db_pool_size,
        max_overflow=config.db_max_overflow,
        pool_timeout=config.db_pool_timeout,
    )
    _session_factory = async_sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


async def close_database() -> None:
    global _engine, _session_factory
    if _engine is not None:
        logger.info("Disposing database engine.")
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        init_database()
    if _engine is None:
        raise RuntimeError("Database engine is not initialized.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        init_database()
    if _session_factory is None:
        raise RuntimeError("Database session factory is not initialized.")
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        init_database()
    if _session_factory is None:
        raise RuntimeError("Database session factory is not initialized.")
    async with _session_factory() as session:
        yield session


async def check_database_connection() -> bool:
    if _engine is None:
        init_database()
    if _engine is None:
        logger.error("Database engine is not initialized.")
        return False
    async with _engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    logger.debug("Database connection check succeeded.")
    return True
