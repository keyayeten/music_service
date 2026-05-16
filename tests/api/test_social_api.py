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
        json={"display_name": "Composer Stage5", "bio": "Bio", "country_code": "UA"},
    )
    assert response.status_code == 200


def _create_and_publish_track(client, access_token: str) -> str:
    create_response = client.post(
        "/api/v1/catalog/tracks",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": "Stage5 Track", "description": "Track for social tests", "duration_seconds": 220},
    )
    assert create_response.status_code == 201
    track_id = create_response.json()["id"]
    publish_response = client.post(
        f"/api/v1/catalog/tracks/{track_id}/publish",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert publish_response.status_code == 200
    return track_id


def _create_playlist(client, access_token: str, *, visibility: str) -> str:
    response = client.post(
        "/api/v1/library/playlists",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": "Stage5 Playlist", "description": "Social access", "visibility": visibility},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.api
def test_like_and_unlike_track_are_idempotent_and_update_counters(client, db_session, redis_client) -> None:
    owner = _signup(client)
    _ensure_composer_profile(client, db_session, owner["user"]["id"], owner["tokens"]["access_token"])
    track_id = _create_and_publish_track(client, owner["tokens"]["access_token"])

    listener = _signup(client)
    listener_access = listener["tokens"]["access_token"]

    first_like = client.post(
        f"/api/v1/social/track/{track_id}/like",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert first_like.status_code == 200
    assert first_like.json()["likes_count"] == 1
    library_after_like = client.get(
        "/api/v1/library/items",
        params={"section": "favorites", "item_type": "track"},
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert library_after_like.status_code == 200
    assert track_id in {item["item_id"] for item in library_after_like.json()["items"]}

    second_like = client.post(
        f"/api/v1/social/track/{track_id}/like",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert second_like.status_code == 200
    assert second_like.json()["likes_count"] == 1

    first_unlike = client.delete(
        f"/api/v1/social/track/{track_id}/like",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert first_unlike.status_code == 200
    assert first_unlike.json()["likes_count"] == 0

    second_unlike = client.delete(
        f"/api/v1/social/track/{track_id}/like",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert second_unlike.status_code == 200
    assert second_unlike.json()["likes_count"] == 0
    library_after_unlike = client.get(
        "/api/v1/library/items",
        params={"section": "favorites", "item_type": "track"},
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert library_after_unlike.status_code == 200
    assert track_id not in {item["item_id"] for item in library_after_unlike.json()["items"]}

    card_response = client.get(f"/api/v1/catalog/tracks/{track_id}")
    assert card_response.status_code == 200
    assert card_response.json()["likes_count"] == 0


@pytest.mark.api
def test_comment_and_reply_update_track_counters(client, db_session, redis_client) -> None:
    owner = _signup(client)
    _ensure_composer_profile(client, db_session, owner["user"]["id"], owner["tokens"]["access_token"])
    track_id = _create_and_publish_track(client, owner["tokens"]["access_token"])

    listener = _signup(client)
    listener_access = listener["tokens"]["access_token"]

    root_comment = client.post(
        f"/api/v1/social/track/{track_id}/comments",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"body": "Great track"},
    )
    assert root_comment.status_code == 200
    assert root_comment.json()["counters"]["comments_count"] == 1
    root_comment_id = root_comment.json()["comment"]["id"]

    reply_comment = client.post(
        f"/api/v1/social/track/{track_id}/comments",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"body": "Listening again", "parent_comment_id": root_comment_id},
    )
    assert reply_comment.status_code == 200
    assert reply_comment.json()["comment"]["parent_comment_id"] == root_comment_id
    assert reply_comment.json()["counters"]["comments_count"] == 2
    reply_comment_id = reply_comment.json()["comment"]["id"]

    list_comments = client.get(
        f"/api/v1/social/track/{track_id}/comments",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert list_comments.status_code == 200
    listed_ids = {item["id"] for item in list_comments.json()["items"]}
    assert root_comment_id in listed_ids
    assert reply_comment_id in listed_ids

    get_reply = client.get(
        f"/api/v1/social/track/{track_id}/comments/{reply_comment_id}",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert get_reply.status_code == 200
    assert get_reply.json()["id"] == reply_comment_id

    card_response = client.get(f"/api/v1/catalog/tracks/{track_id}")
    assert card_response.status_code == 200
    assert card_response.json()["comments_count"] == 2


@pytest.mark.api
def test_reply_rejects_parent_from_other_target(client, db_session, redis_client) -> None:
    owner = _signup(client)
    _ensure_composer_profile(client, db_session, owner["user"]["id"], owner["tokens"]["access_token"])
    first_track_id = _create_and_publish_track(client, owner["tokens"]["access_token"])
    second_track_id = _create_and_publish_track(client, owner["tokens"]["access_token"])

    listener = _signup(client)
    listener_access = listener["tokens"]["access_token"]

    root_comment = client.post(
        f"/api/v1/social/track/{first_track_id}/comments",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"body": "Comment on first track"},
    )
    assert root_comment.status_code == 200
    root_comment_id = root_comment.json()["comment"]["id"]

    invalid_reply = client.post(
        f"/api/v1/social/track/{second_track_id}/comments",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"body": "Invalid reply", "parent_comment_id": root_comment_id},
    )
    assert invalid_reply.status_code == 400
    assert invalid_reply.json()["detail"]["code"] == "validation_error"


@pytest.mark.api
def test_unlisted_playlist_comment_is_available_by_direct_link(client, db_session, redis_client) -> None:
    owner = _signup(client)
    owner_access = owner["tokens"]["access_token"]
    playlist_id = _create_playlist(client, owner_access, visibility="unlisted")

    list_public = client.get("/api/v1/library/playlists/public")
    assert list_public.status_code == 200
    assert playlist_id not in {item["id"] for item in list_public.json()["items"]}

    listener = _signup(client)
    listener_access = listener["tokens"]["access_token"]
    comment_response = client.post(
        f"/api/v1/social/playlist/{playlist_id}/comments",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"body": "Found by direct link"},
    )
    assert comment_response.status_code == 200
    assert comment_response.json()["comment"]["target_type"] == "playlist"
