import pytest
from sqlalchemy import text


@pytest.mark.integration
def test_db_session_executes_simple_query(db_session) -> None:
    value = db_session.execute(text("SELECT 1")).scalar_one()
    assert value == 1


@pytest.mark.integration
def test_redis_client_roundtrip(redis_client) -> None:
    key = "stage0:integration:ping"
    redis_client.setex(key, 30, "ok")
    assert redis_client.get(key) == "ok"
