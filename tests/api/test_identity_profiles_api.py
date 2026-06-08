from uuid import uuid4

import pytest
from sqlalchemy import text


def _signup(client) -> dict:
    marker = uuid4().hex[:10]
    payload = {
        "email": f"{marker}@example.com",
        "username": f"user_{marker}",
        "password": "StrongPassword123!",
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    return response.json()


def _grant_composer_role(db_session, user_id: str) -> None:
    role_id = db_session.execute(text("SELECT id FROM roles WHERE code = 'composer'")).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO user_roles (user_id, role_id)
            VALUES (:user_id, :role_id)
            ON CONFLICT (user_id, role_id) DO NOTHING
            """
        ),
        {"user_id": user_id, "role_id": role_id},
    )
    db_session.commit()


@pytest.mark.api
def test_get_my_profile_requires_authentication(client, db_session, redis_client) -> None:
    response = client.get("/api/v1/profiles/me")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_error"


@pytest.mark.api
def test_get_my_profile_returns_identity_payload(client, db_session, redis_client) -> None:
    signup_payload = _signup(client)
    access_token = signup_payload["tokens"]["access_token"]

    response = client.get(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == signup_payload["user"]["email"]
    assert body["composer_profile"] is None


@pytest.mark.api
def test_update_my_profile_returns_403_without_composer_role(
    client, db_session, redis_client
) -> None:
    signup_payload = _signup(client)
    access_token = signup_payload["tokens"]["access_token"]

    response = client.patch(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"display_name": "Composer Name", "bio": "Bio", "country_code": "UA"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "authorization_error"


@pytest.mark.api
def test_update_my_profile_validates_payload(client, db_session, redis_client) -> None:
    signup_payload = _signup(client)
    user_id = signup_payload["user"]["id"]
    access_token = signup_payload["tokens"]["access_token"]
    _grant_composer_role(db_session, user_id)

    response = client.patch(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"display_name": "A", "bio": "Bio", "country_code": "UA"},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "validation_error"


@pytest.mark.api
def test_update_my_profile_creates_composer_profile_and_link(
    client, db_session, redis_client
) -> None:
    signup_payload = _signup(client)
    user_id = signup_payload["user"]["id"]
    access_token = signup_payload["tokens"]["access_token"]
    _grant_composer_role(db_session, user_id)

    response = client.patch(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"display_name": "Composer Name", "bio": "Short bio", "country_code": "ua"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["composer_profile"] is not None
    assert body["composer_profile"]["display_name"] == "Composer Name"
    assert body["composer_profile"]["country_code"] == "UA"

    role_profile_row = (
        db_session.execute(
            text(
                """
            SELECT profile_type, profile_id
            FROM user_role_profiles
            WHERE user_id = :user_id
            """
            ),
            {"user_id": user_id},
        )
        .mappings()
        .one()
    )
    assert role_profile_row["profile_type"] == "composer_profile"
    assert str(role_profile_row["profile_id"]) == body["composer_profile"]["id"]
