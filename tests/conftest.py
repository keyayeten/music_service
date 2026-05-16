from collections.abc import Generator
import socket
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config.settings import get_settings
from backend.infrastructure.cache.redis_client import get_redis_client
from backend.infrastructure.persistence.database import get_session
from backend.main import create_app


@pytest.fixture(scope="session")
def app():
    return create_app()


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
    parsed = urlparse(settings.database_url.replace("postgresql+psycopg://", "postgresql://"))
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
    session_generator = get_session()
    session = next(session_generator)
    _require_db(session)
    try:
        yield session
    finally:
        session_generator.close()


@pytest.fixture()
def redis_client() -> Redis:
    _require_redis_service()
    redis_instance = get_redis_client()
    _require_redis(redis_instance)
    return redis_instance
