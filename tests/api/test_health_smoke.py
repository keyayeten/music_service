import pytest


@pytest.mark.api
def test_system_health_endpoint_smoke(client, db_session, redis_client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
    assert payload["redis"] == "ok"


@pytest.mark.api
def test_v1_health_endpoint_smoke(client, db_session, redis_client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == "v1"
    assert payload["database"] == "ok"
    assert payload["redis"] == "ok"
