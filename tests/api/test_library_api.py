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
        json={"display_name": "Composer Stage4", "bio": "Bio", "country_code": "UA"},
    )
    assert response.status_code == 200


def _create_track(client, access_token: str) -> str:
    response = client.post(
        "/api/v1/catalog/tracks",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": "Stage4 Track", "description": "Test track", "duration_seconds": 210},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.api
def test_playlist_owner_crud_and_public_visibility(client, db_session, redis_client) -> None:
    signup_payload = _signup(client)
    user_id = signup_payload["user"]["id"]
    access_token = signup_payload["tokens"]["access_token"]
    _ensure_composer_profile(client, db_session, user_id, access_token)
    track_id = _create_track(client, access_token)

    create_response = client.post(
        "/api/v1/library/playlists",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": "My Playlist", "description": "Stage4", "visibility": "private"},
    )
    assert create_response.status_code == 201
    playlist_id = create_response.json()["id"]

    add_track_response = client.post(
        f"/api/v1/library/playlists/{playlist_id}/tracks",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"track_id": track_id},
    )
    assert add_track_response.status_code == 200
    assert len(add_track_response.json()["track_items"]) == 1

    reorder_response = client.put(
        f"/api/v1/library/playlists/{playlist_id}/tracks/reorder",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"track_ids": [track_id]},
    )
    assert reorder_response.status_code == 200
    assert reorder_response.json()["track_items"][0]["position"] == 1

    hidden_public_response = client.get(f"/api/v1/library/playlists/public/{playlist_id}")
    assert hidden_public_response.status_code == 404

    update_visibility_response = client.patch(
        f"/api/v1/library/playlists/{playlist_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": "My Playlist", "description": "Stage4", "visibility": "public"},
    )
    assert update_visibility_response.status_code == 200
    assert update_visibility_response.json()["visibility"] == "public"

    list_public_response = client.get("/api/v1/library/playlists/public")
    assert list_public_response.status_code == 200
    assert playlist_id in {item["id"] for item in list_public_response.json()["items"]}

    remove_track_response = client.delete(
        f"/api/v1/library/playlists/{playlist_id}/tracks/{track_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert remove_track_response.status_code == 200
    assert remove_track_response.json()["track_items"] == []

    delete_response = client.delete(
        f"/api/v1/library/playlists/{playlist_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert delete_response.status_code == 204


@pytest.mark.api
def test_non_owner_cannot_modify_playlist(client, db_session, redis_client) -> None:
    owner_signup = _signup(client)
    owner_access = owner_signup["tokens"]["access_token"]

    create_response = client.post(
        "/api/v1/library/playlists",
        headers={"Authorization": f"Bearer {owner_access}"},
        json={"title": "Owner Playlist", "description": None, "visibility": "private"},
    )
    assert create_response.status_code == 201
    playlist_id = create_response.json()["id"]

    attacker_signup = _signup(client)
    attacker_access = attacker_signup["tokens"]["access_token"]

    forbidden_response = client.patch(
        f"/api/v1/library/playlists/{playlist_id}",
        headers={"Authorization": f"Bearer {attacker_access}"},
        json={"title": "Hacked", "description": None, "visibility": "public"},
    )
    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["detail"]["code"] == "authorization_error"


@pytest.mark.api
def test_library_items_crud_and_duplicate_conflict(client, db_session, redis_client) -> None:
    signup_payload = _signup(client)
    user_id = signup_payload["user"]["id"]
    access_token = signup_payload["tokens"]["access_token"]
    _ensure_composer_profile(client, db_session, user_id, access_token)
    track_id = _create_track(client, access_token)

    add_response = client.post(
        "/api/v1/library/items",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"item_type": "track", "item_id": track_id, "section": "favorites"},
    )
    assert add_response.status_code == 201

    duplicate_response = client.post(
        "/api/v1/library/items",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"item_type": "track", "item_id": track_id, "section": "favorites"},
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"]["code"] == "conflict_error"

    list_response = client.get(
        "/api/v1/library/items?section=favorites",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1

    delete_response = client.delete(
        f"/api/v1/library/items/track/{track_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert delete_response.status_code == 204

    list_after_delete = client.get(
        "/api/v1/library/items?section=favorites",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert list_after_delete.status_code == 200
    assert list_after_delete.json()["items"] == []
