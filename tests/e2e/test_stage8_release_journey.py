from uuid import uuid4

import pytest
from sqlalchemy import text


def _signup(client) -> dict:
    marker = uuid4().hex[:10]
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"{marker}@example.com",
            "username": f"user_{marker}",
            "password": "StrongPassword123!",
        },
    )
    assert response.status_code == 201
    return response.json()


def _login(client, username: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": username, "password": "StrongPassword123!"},
    )
    assert response.status_code == 200
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


@pytest.mark.e2e
def test_stage8_registration_login_and_content_journey(client, db_session) -> None:
    signup_payload = _signup(client)
    user_id = signup_payload["user"]["id"]
    username = signup_payload["user"]["username"]

    login_payload = _login(client, username)
    access_token = login_payload["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    _grant_composer_role(db_session, user_id)

    profile_response = client.patch(
        "/api/v1/profiles/me",
        headers=headers,
        json={"display_name": "Stage8 Composer", "bio": "E2E profile", "country_code": "UA"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["composer_profile"]["display_name"] == "Stage8 Composer"

    create_track_response = client.post(
        "/api/v1/catalog/tracks",
        headers=headers,
        json={
            "title": "Stage8 E2E Track",
            "description": "End-to-end flow",
            "duration_seconds": 210,
        },
    )
    assert create_track_response.status_code == 201
    track_id = create_track_response.json()["id"]

    publish_track_response = client.post(
        f"/api/v1/catalog/tracks/{track_id}/publish", headers=headers
    )
    assert publish_track_response.status_code == 200
    assert publish_track_response.json()["status"] == "published"

    create_album_response = client.post(
        "/api/v1/catalog/albums",
        headers=headers,
        json={"title": "Stage8 E2E Album", "description": "End-to-end album"},
    )
    assert create_album_response.status_code == 201
    album_id = create_album_response.json()["id"]

    set_album_tracks_response = client.put(
        f"/api/v1/catalog/albums/{album_id}/tracks",
        headers=headers,
        json={"track_ids": [track_id]},
    )
    assert set_album_tracks_response.status_code == 200

    publish_album_response = client.post(
        f"/api/v1/catalog/albums/{album_id}/publish", headers=headers
    )
    assert publish_album_response.status_code == 200
    assert publish_album_response.json()["status"] == "published"

    public_tracks_response = client.get("/api/v1/catalog/tracks")
    assert public_tracks_response.status_code == 200
    assert track_id in {item["id"] for item in public_tracks_response.json()["items"]}

    public_album_response = client.get(f"/api/v1/catalog/albums/{album_id}")
    assert public_album_response.status_code == 200
    assert public_album_response.json()["id"] == album_id
