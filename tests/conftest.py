import asyncio
from collections.abc import Generator
import socket
import sys
from urllib.parse import urlparse

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
from fastapi.testclient import TestClient
from redis import Redis
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from backend.config.settings import get_settings
from backend.infrastructure.persistence.database import close_database
from backend.main import create_app
from tests.async_tools import run_async


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture()
def admin_enabled_app(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ADMIN_ENABLED", "true")
    get_settings.cache_clear()
    application = create_app()
    yield application
    run_async(close_database())
    get_settings.cache_clear()


def _service_ready(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture()
def client(app, db_session, redis_client) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def _require_db_service() -> None:
    settings = get_settings()
    parsed = urlparse(
        settings.database_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")
    )
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    if not _service_ready(host, port):
        pytest.skip(f"PostgreSQL is unavailable on {host}:{port}")


def _require_db(session: Session) -> None:
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - infrastructure guard
        pytest.skip(f"PostgreSQL is unavailable for this test run: {exc}")


def _require_redis_service() -> None:
    settings = get_settings()
    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    if not _service_ready(host, port):
        pytest.skip(f"Redis is unavailable on {host}:{port}")


def _require_redis(client: Redis) -> None:
    try:
        client.ping()
    except Exception as exc:  # pragma: no cover - infrastructure guard
        pytest.skip(f"Redis is unavailable for this test run: {exc}")


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    _require_db_service()
    settings = get_settings()
    sync_database_url = settings.database_url.replace("+asyncpg", "+psycopg")
    engine = create_engine(sync_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = session_factory()
    _require_db(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def redis_client() -> Generator[Redis, None, None]:
    _require_redis_service()
    redis_instance = Redis.from_url(get_settings().redis_url, decode_responses=True)
    _require_redis(redis_instance)
    try:
        yield redis_instance
    finally:
        redis_instance.close()
