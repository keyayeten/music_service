import os
import time

from dotenv import load_dotenv
from redis import Redis
from sqlalchemy import create_engine, text

load_dotenv()


def _database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://music_user:music_password@localhost:5432/music_service",
    )


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


def wait_for_postgres(timeout_seconds: int = 60) -> None:
    engine = create_engine(_database_url(), pool_pre_ping=True)
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover - best effort readiness
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"PostgreSQL is not ready: {last_error}")


def wait_for_redis(timeout_seconds: int = 60) -> None:
    client = Redis.from_url(_redis_url(), decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            if client.ping():
                return
        except Exception as exc:  # pragma: no cover - best effort readiness
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"Redis is not ready: {last_error}")


def main() -> None:
    wait_for_postgres()
    wait_for_redis()
    print("PostgreSQL and Redis are ready")


if __name__ == "__main__":
    main()
