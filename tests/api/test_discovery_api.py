from __future__ import annotations

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
        json={"display_name": "Composer Stage6", "bio": "Bio", "country_code": "UA"},
    )
    assert response.status_code == 200


def _create_and_publish_track(client, access_token: str, *, title: str) -> str:
    create_response = client.post(
        "/api/v1/catalog/tracks",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": title, "description": "Track for Stage6", "duration_seconds": 210},
    )
    assert create_response.status_code == 201
    track_id = create_response.json()["id"]
    publish_response = client.post(
        f"/api/v1/catalog/tracks/{track_id}/publish",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert publish_response.status_code == 200
    return track_id


@pytest.mark.api
def test_key_stage6_actions_create_events_and_external_click_rows(client, db_session, redis_client) -> None:
    owner = _signup(client)
    _ensure_composer_profile(client, db_session, owner["user"]["id"], owner["tokens"]["access_token"])
    track_id = _create_and_publish_track(client, owner["tokens"]["access_token"], title="Stage6 Event Track")

    album_response = client.post(
        "/api/v1/catalog/albums",
        headers={"Authorization": f"Bearer {owner['tokens']['access_token']}"},
        json={"title": "Stage6 Album", "description": "Album for save-event mapping"},
    )
    assert album_response.status_code == 201
    album_id = album_response.json()["id"]
    set_tracks_response = client.put(
        f"/api/v1/catalog/albums/{album_id}/tracks",
        headers={"Authorization": f"Bearer {owner['tokens']['access_token']}"},
        json={"track_ids": [track_id]},
    )
    assert set_tracks_response.status_code == 200
    publish_album_response = client.post(
        f"/api/v1/catalog/albums/{album_id}/publish",
        headers={"Authorization": f"Bearer {owner['tokens']['access_token']}"},
    )
    assert publish_album_response.status_code == 200

    db_session.execute(
        text(
            """
            INSERT INTO external_links (id, entity_type, entity_id, service, url, is_primary)
            VALUES (:id, 'track', :entity_id, 'other', :url, false)
            """
        ),
        {
            "id": str(uuid4()),
            "entity_id": track_id,
            "url": f"https://music.example/{uuid4().hex}",
        },
    )
    external_link_id = db_session.execute(
        text(
            """
            SELECT id
            FROM external_links
            WHERE entity_type = 'track' AND entity_id = :track_id
            """
        ),
        {"track_id": track_id},
    ).scalar_one()
    db_session.commit()

    listener = _signup(client)
    listener_access = listener["tokens"]["access_token"]
    listener_id = listener["user"]["id"]

    playlist_response = client.post(
        "/api/v1/library/playlists",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"title": "Stage6 Playlist", "description": "Discovery playlist", "visibility": "private"},
    )
    assert playlist_response.status_code == 201
    playlist_id = playlist_response.json()["id"]

    add_playlist_track_response = client.post(
        f"/api/v1/library/playlists/{playlist_id}/tracks",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"track_id": track_id},
    )
    assert add_playlist_track_response.status_code == 200

    list_tracks_response = client.get(
        "/api/v1/catalog/tracks",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert list_tracks_response.status_code == 200

    get_track_response = client.get(
        f"/api/v1/catalog/tracks/{track_id}",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert get_track_response.status_code == 200

    save_track_response = client.post(
        "/api/v1/library/items",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"item_type": "track", "item_id": track_id, "section": "favorites"},
    )
    assert save_track_response.status_code == 201
    save_album_response = client.post(
        "/api/v1/library/items",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"item_type": "album", "item_id": album_id, "section": "albums"},
    )
    assert save_album_response.status_code == 201
    save_playlist_response = client.post(
        "/api/v1/library/items",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"item_type": "playlist", "item_id": playlist_id, "section": "playlists"},
    )
    assert save_playlist_response.status_code == 201

    like_response = client.post(
        f"/api/v1/social/track/{track_id}/like",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert like_response.status_code == 200

    comment_response = client.post(
        f"/api/v1/social/track/{track_id}/comments",
        headers={"Authorization": f"Bearer {listener_access}"},
        json={"body": "Stage6 comment"},
    )
    assert comment_response.status_code == 200

    external_click_response = client.post(
        f"/api/v1/catalog/external-links/{external_link_id}/click",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert external_click_response.status_code == 200

    event_types = {
        row.event_type
        for row in db_session.execute(
            text(
                """
                SELECT DISTINCT event_type
                FROM user_track_events
                WHERE user_id = :user_id
                """
            ),
            {"user_id": listener_id},
        ).all()
    }
    assert event_types == {"view", "like", "save", "comment", "playlist_add", "external_click"}
    click_rows = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM external_link_clicks
            WHERE user_id = :user_id AND external_link_id = :external_link_id
            """
        ),
        {"user_id": listener_id, "external_link_id": external_link_id},
    ).scalar_one()
    assert click_rows == 1


@pytest.mark.api
def test_recommendations_support_personalized_and_fallback_modes(client, db_session, redis_client) -> None:
    owner = _signup(client)
    _ensure_composer_profile(client, db_session, owner["user"]["id"], owner["tokens"]["access_token"])
    top_track_id = _create_and_publish_track(client, owner["tokens"]["access_token"], title="Stage6 Reco Top")
    secondary_track_id = _create_and_publish_track(client, owner["tokens"]["access_token"], title="Stage6 Reco Secondary")

    db_session.execute(text("UPDATE tracks SET likes_count = 100000 WHERE id = :track_id"), {"track_id": top_track_id})
    db_session.execute(text("UPDATE tracks SET likes_count = 1 WHERE id = :track_id"), {"track_id": secondary_track_id})
    db_session.commit()

    listener = _signup(client)
    listener_access = listener["tokens"]["access_token"]
    listener_id = listener["user"]["id"]
    db_session.execute(
        text(
            """
            INSERT INTO user_track_events (id, user_id, track_id, event_type)
            VALUES (:id, :user_id, :track_id, 'like')
            """
        ),
        {"id": str(uuid4()), "user_id": listener_id, "track_id": secondary_track_id},
    )
    db_session.execute(
        text(
            """
            INSERT INTO user_track_events (id, user_id, track_id, event_type)
            VALUES (:id, :user_id, :track_id, 'external_click')
            """
        ),
        {"id": str(uuid4()), "user_id": listener_id, "track_id": secondary_track_id},
    )
    db_session.commit()

    personalized = client.get(
        "/api/v1/discovery/recommendations/tracks?limit=2",
        headers={"Authorization": f"Bearer {listener_access}"},
    )
    assert personalized.status_code == 200
    personalized_items = personalized.json()["items"]
    assert personalized_items[0]["track_id"] == secondary_track_id
    assert personalized_items[0]["source"] == "personalized"

    fallback_for_new_user = client.get("/api/v1/discovery/recommendations/tracks?limit=2")
    assert fallback_for_new_user.status_code == 200
    fallback_items = fallback_for_new_user.json()["items"]
    assert fallback_items[0]["track_id"] == top_track_id
    assert fallback_items[0]["source"] == "top_published"
