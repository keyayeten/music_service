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


def _grant_role(db_session, user_id: str, role_code: str) -> None:
    role_id = db_session.execute(text("SELECT id FROM roles WHERE code = :code"), {"code": role_code}).scalar_one()
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


def _ensure_composer_profile(client, db_session, user_id: str, access_token: str) -> None:
    _grant_role(db_session, user_id, "composer")
    response = client.patch(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"display_name": "Composer Stage3", "bio": "Bio", "country_code": "UA"},
    )
    assert response.status_code == 200


@pytest.mark.api
def test_create_and_publish_track_as_composer(client, db_session, redis_client) -> None:
    signup_payload = _signup(client)
    user_id = signup_payload["user"]["id"]
    access_token = signup_payload["tokens"]["access_token"]
    _ensure_composer_profile(client, db_session, user_id, access_token)

    create_response = client.post(
        "/api/v1/catalog/tracks",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": "Stage3 Track", "description": "Test track", "duration_seconds": 215},
    )
    assert create_response.status_code == 201
    track_id = create_response.json()["id"]
    assert create_response.json()["status"] == "draft"

    publish_response = client.post(
        f"/api/v1/catalog/tracks/{track_id}/publish",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"


@pytest.mark.api
def test_replace_album_tracks_requires_owner_permissions(client, db_session, redis_client) -> None:
    first_user = _signup(client)
    first_user_id = first_user["user"]["id"]
    first_access = first_user["tokens"]["access_token"]
    _ensure_composer_profile(client, db_session, first_user_id, first_access)

    second_user = _signup(client)
    second_user_id = second_user["user"]["id"]
    second_access = second_user["tokens"]["access_token"]
    _ensure_composer_profile(client, db_session, second_user_id, second_access)

    track_response = client.post(
        "/api/v1/catalog/tracks",
        headers={"Authorization": f"Bearer {first_access}"},
        json={"title": "Album Track", "description": None, "duration_seconds": 180},
    )
    assert track_response.status_code == 201
    track_id = track_response.json()["id"]

    album_response = client.post(
        "/api/v1/catalog/albums",
        headers={"Authorization": f"Bearer {first_access}"},
        json={"title": "Album", "description": "Owned by first"},
    )
    assert album_response.status_code == 201
    album_id = album_response.json()["id"]

    forbidden_response = client.put(
        f"/api/v1/catalog/albums/{album_id}/tracks",
        headers={"Authorization": f"Bearer {second_access}"},
        json={"track_ids": [track_id]},
    )
    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["detail"]["code"] == "authorization_error"
