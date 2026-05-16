from uuid import uuid4

import pytest


def _credentials() -> tuple[str, str, str]:
    marker = uuid4().hex[:10]
    return f"user_{marker}", f"{marker}@example.com", "StrongPassword123!"


@pytest.mark.api
def test_signup_login_me_refresh_flow(client, db_session, redis_client) -> None:
    username, email, password = _credentials()

    signup_response = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "username": username, "password": password},
    )
    assert signup_response.status_code == 201
    signup_payload = signup_response.json()
    assert signup_payload["user"]["email"] == email
    assert "user" in signup_payload["user"]["roles"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"login": username, "password": password},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    access_token = login_payload["tokens"]["access_token"]
    refresh_token = login_payload["tokens"]["refresh_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["username"] == username
    assert me_payload["email"] == email

    refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    refreshed_payload = refresh_response.json()
    assert refreshed_payload["tokens"]["access_token"] != ""
    assert refreshed_payload["tokens"]["refresh_token"] != ""


@pytest.mark.api
def test_me_returns_401_without_token(client, db_session, redis_client) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    payload = response.json()
    assert payload["detail"]["code"] == "authentication_error"


@pytest.mark.api
def test_login_returns_predictable_error_for_invalid_credentials(client, db_session, redis_client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "unknown_user", "password": "InvalidPassword123!"},
    )
    assert response.status_code == 401
    payload = response.json()
    assert payload["detail"]["code"] == "authentication_error"
