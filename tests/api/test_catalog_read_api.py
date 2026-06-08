from uuid import uuid4

import pytest
from sqlalchemy import text

from backend.config.settings import get_settings


def _seed_catalog_read_data(db_session) -> dict[str, str]:
    user_id = str(uuid4())
    composer_profile_id = str(uuid4())
    published_track_id = str(uuid4())
    draft_track_id = str(uuid4())
    published_album_id = str(uuid4())
    draft_album_id = str(uuid4())
    rock_genre_id = str(uuid4())
    db_session.execute(
        text(
            """
            INSERT INTO users (id, email, username, password_hash, status)
            VALUES (:id, :email, :username, :password_hash, :status)
            """
        ),
        {
            "id": user_id,
            "email": f"{uuid4().hex}@example.com",
            "username": f"user_{uuid4().hex[:8]}",
            "password_hash": "hash",
            "status": "active",
        },
    )
    db_session.execute(
        text(
            """
            INSERT INTO composer_profiles (id, user_id, display_name, bio, country_code, verified)
            VALUES (:id, :user_id, :display_name, :bio, :country_code, :verified)
            """
        ),
        {
            "id": composer_profile_id,
            "user_id": user_id,
            "display_name": "Read Composer",
            "bio": "Bio",
            "country_code": "UA",
            "verified": False,
        },
    )
    genre_code = f"rock_{uuid4().hex[:6]}"
    db_session.execute(
        text(
            """
            INSERT INTO genres (id, code, name)
            VALUES (:id, :code, :name)
            """
        ),
        {"id": rock_genre_id, "code": genre_code, "name": "Rock"},
    )
    for track_id, title, status_value in (
        (published_track_id, "Public Track", "published"),
        (draft_track_id, "Hidden Track", "draft"),
    ):
        db_session.execute(
            text(
                """
                INSERT INTO tracks (id, title, status, duration_seconds, plays_count, likes_count, comments_count)
                VALUES (:id, :title, :status, 210, 0, 0, 0)
                """
            ),
            {"id": track_id, "title": title, "status": status_value},
        )
        db_session.execute(
            text(
                """
                INSERT INTO track_authors (track_id, composer_profile_id, contribution_role, position)
                VALUES (:track_id, :composer_profile_id, 'composer', 1)
                """
            ),
            {"track_id": track_id, "composer_profile_id": composer_profile_id},
        )
    db_session.execute(
        text(
            """
            INSERT INTO track_genres (track_id, genre_id)
            VALUES (:track_id, :genre_id)
            """
        ),
        {"track_id": published_track_id, "genre_id": rock_genre_id},
    )
    for album_id, title, status_value in (
        (published_album_id, "Public Album", "published"),
        (draft_album_id, "Draft Album", "draft"),
    ):
        db_session.execute(
            text(
                """
                INSERT INTO albums (id, owner_composer_id, title, status, likes_count, comments_count)
                VALUES (:id, :owner_composer_id, :title, :status, 0, 0)
                """
            ),
            {
                "id": album_id,
                "owner_composer_id": composer_profile_id,
                "title": title,
                "status": status_value,
            },
        )
    db_session.commit()
    return {
        "published_track_id": published_track_id,
        "draft_track_id": draft_track_id,
        "published_album_id": published_album_id,
        "draft_album_id": draft_album_id,
        "genre_code": genre_code,
    }


def _clear_cache_namespace(redis_client, namespace: str) -> None:
    prefix = get_settings().redis_key_prefix
    pattern = f"{prefix}:http:{namespace}:*"
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)


@pytest.mark.api
def test_anonymous_catalog_list_returns_only_published_entities(
    client, db_session, redis_client
) -> None:
    _clear_cache_namespace(redis_client, "catalog:albums:list")
    seeded = _seed_catalog_read_data(db_session)

    tracks_response = client.get("/api/v1/catalog/tracks")
    assert tracks_response.status_code == 200
    track_ids = {item["id"] for item in tracks_response.json()["items"]}
    assert seeded["published_track_id"] in track_ids
    assert seeded["draft_track_id"] not in track_ids

    albums_response = client.get("/api/v1/catalog/albums")
    assert albums_response.status_code == 200
    album_ids = {item["id"] for item in albums_response.json()["items"]}
    assert seeded["published_album_id"] in album_ids
    assert seeded["draft_album_id"] not in album_ids


@pytest.mark.api
def test_catalog_track_filters_by_genre(client, db_session, redis_client) -> None:
    seeded = _seed_catalog_read_data(db_session)

    response = client.get("/api/v1/catalog/tracks", params={"genre": seeded["genre_code"]})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["genre_codes"] == [seeded["genre_code"]]


@pytest.mark.api
def test_anonymous_track_detail_rejects_unpublished_track(client, db_session, redis_client) -> None:
    seeded = _seed_catalog_read_data(db_session)

    response = client.get(f"/api/v1/catalog/tracks/{seeded['draft_track_id']}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


@pytest.mark.api
def test_catalog_albums_list_uses_cache_with_ttl_staleness(
    client, db_session, redis_client
) -> None:
    _clear_cache_namespace(redis_client, "catalog:albums:list")
    seeded = _seed_catalog_read_data(db_session)

    first_response = client.get("/api/v1/catalog/albums")
    assert first_response.status_code == 200
    first_titles = {item["id"]: item["title"] for item in first_response.json()["items"]}
    assert first_titles[seeded["published_album_id"]] == "Public Album"

    db_session.execute(
        text("UPDATE albums SET title = :title WHERE id = :album_id"),
        {"title": "Public Album Updated", "album_id": seeded["published_album_id"]},
    )
    db_session.commit()

    second_response = client.get("/api/v1/catalog/albums")
    assert second_response.status_code == 200
    second_titles = {item["id"]: item["title"] for item in second_response.json()["items"]}
    assert second_titles[seeded["published_album_id"]] == "Public Album"


@pytest.mark.api
def test_catalog_album_detail_uses_cache_with_ttl_staleness(
    client, db_session, redis_client
) -> None:
    _clear_cache_namespace(redis_client, "catalog:albums:get")
    seeded = _seed_catalog_read_data(db_session)

    first_response = client.get(f"/api/v1/catalog/albums/{seeded['published_album_id']}")
    assert first_response.status_code == 200
    assert first_response.json()["title"] == "Public Album"

    db_session.execute(
        text("UPDATE albums SET title = :title WHERE id = :album_id"),
        {"title": "Public Album Updated", "album_id": seeded["published_album_id"]},
    )
    db_session.commit()

    second_response = client.get(f"/api/v1/catalog/albums/{seeded['published_album_id']}")
    assert second_response.status_code == 200
    assert second_response.json()["title"] == "Public Album"
