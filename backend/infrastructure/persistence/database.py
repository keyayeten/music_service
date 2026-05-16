from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import Settings, get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def init_database(settings: Settings | None = None) -> None:
    global _engine, _session_factory
    config = settings or get_settings()
    if _engine is not None:
        return
    _engine = create_engine(
        config.database_url,
        echo=config.db_echo,
        pool_pre_ping=True,
        pool_size=config.db_pool_size,
        max_overflow=config.db_max_overflow,
        pool_timeout=config.db_pool_timeout,
    )
    _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


def close_database() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def get_session() -> Generator[Session, None, None]:
    if _session_factory is None:
        init_database()
    if _session_factory is None:
        raise RuntimeError("Database session factory is not initialized.")
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


def check_database_connection() -> bool:
    if _engine is None:
        init_database()
    if _engine is None:
        return False
    with _engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
