from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def _insert_user(db_session) -> str:
    user_id = str(uuid4())
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
            "username": f"user_{uuid4().hex[:10]}",
            "password_hash": "hash",
            "status": "active",
        },
    )
    db_session.commit()
    return user_id


def _insert_composer_profile(db_session, user_id: str) -> str:
    composer_profile_id = str(uuid4())
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
            "display_name": "Composer",
            "bio": "Bio",
            "country_code": "UA",
            "verified": False,
        },
    )
    db_session.commit()
    return composer_profile_id


@pytest.mark.integration
def test_album_tracks_unique_position_constraint(db_session) -> None:
    user_id = _insert_user(db_session)
    composer_profile_id = _insert_composer_profile(db_session, user_id)
    album_id = str(uuid4())
    first_track_id = str(uuid4())
    second_track_id = str(uuid4())
    db_session.execute(
        text(
            """
            INSERT INTO tracks (id, title, status, duration_seconds, plays_count, likes_count, comments_count)
            VALUES (:id, :title, 'draft', 120, 0, 0, 0)
            """
        ),
        {"id": first_track_id, "title": "Track A"},
    )
    db_session.execute(
        text(
            """
            INSERT INTO tracks (id, title, status, duration_seconds, plays_count, likes_count, comments_count)
            VALUES (:id, :title, 'draft', 120, 0, 0, 0)
            """
        ),
        {"id": second_track_id, "title": "Track B"},
    )
    db_session.execute(
        text(
            """
            INSERT INTO albums (id, owner_composer_id, title, status, likes_count, comments_count)
            VALUES (:id, :owner_composer_id, :title, 'draft', 0, 0)
            """
        ),
        {"id": album_id, "owner_composer_id": composer_profile_id, "title": "Album"},
    )
    db_session.execute(
        text(
            """
            INSERT INTO album_tracks (album_id, track_id, position)
            VALUES (:album_id, :track_id, :position)
            """
        ),
        {"album_id": album_id, "track_id": first_track_id, "position": 1},
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO album_tracks (album_id, track_id, position)
                VALUES (:album_id, :track_id, :position)
                """
            ),
            {"album_id": album_id, "track_id": second_track_id, "position": 1},
        )
        db_session.commit()
    db_session.rollback()


@pytest.mark.integration
def test_external_links_service_check_constraint(db_session) -> None:
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO external_links (id, entity_type, entity_id, service, url, is_primary)
                VALUES (:id, :entity_type, :entity_id, :service, :url, false)
                """
            ),
            {
                "id": str(uuid4()),
                "entity_type": "track",
                "entity_id": str(uuid4()),
                "service": "invalid_service",
                "url": "https://example.com/track",
            },
        )
        db_session.commit()
    db_session.rollback()


@pytest.mark.integration
def test_tags_slug_unique_constraint(db_session) -> None:
    slug = f"tag-{uuid4().hex[:8]}"
    db_session.execute(
        text(
            """
            INSERT INTO tags (id, slug, name)
            VALUES (:id, :slug, :name)
            """
        ),
        {"id": str(uuid4()), "slug": slug, "name": "Tag One"},
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO tags (id, slug, name)
                VALUES (:id, :slug, :name)
                """
            ),
            {"id": str(uuid4()), "slug": slug, "name": "Tag Two"},
        )
        db_session.commit()
    db_session.rollback()
