from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from backend.domain.catalog.repositories import AlbumListFilter, TrackListFilter
from backend.infrastructure.persistence.repositories.catalog import SqlAlchemyCatalogRepository


def _insert_user_and_composer(db_session) -> tuple[str, str]:
    user_id = str(uuid4())
    composer_profile_id = str(uuid4())
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
            "display_name": "Composer",
            "bio": "Bio",
            "country_code": "UA",
            "verified": False,
        },
    )
    db_session.commit()
    return user_id, composer_profile_id


@pytest.mark.integration
def test_list_tracks_returns_only_published_for_public_filter(db_session) -> None:
    _, composer_profile_id = _insert_user_and_composer(db_session)
    published_track_id = str(uuid4())
    draft_track_id = str(uuid4())
    genre_id = str(uuid4())
    genre_code = f"rock_{uuid4().hex[:8]}"
    db_session.execute(
        text(
            """
            INSERT INTO genres (id, code, name)
            VALUES (:id, :code, :name)
            """
        ),
        {"id": genre_id, "code": genre_code, "name": "Rock"},
    )
    for track_id, title, status_value in (
        (published_track_id, "Published Track", "published"),
        (draft_track_id, "Draft Track", "draft"),
    ):
        db_session.execute(
            text(
                """
                INSERT INTO tracks (id, title, status, duration_seconds, plays_count, likes_count, comments_count)
                VALUES (:id, :title, :status, 180, 0, 0, 0)
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
            {"track_id": track_id, "genre_id": genre_id},
        )
    db_session.commit()

    repository = SqlAlchemyCatalogRepository(db_session)
    result = repository.list_tracks(
        TrackListFilter(
            status=None,
            genre_code=genre_code,
            author_id=None,
            include_unpublished=False,
        )
    )

    assert len(result) == 1
    assert result[0].id == UUID(published_track_id)
    assert result[0].status == "published"


@pytest.mark.integration
def test_list_albums_by_owner_and_status(db_session) -> None:
    _, composer_profile_id = _insert_user_and_composer(db_session)
    published_album_id = str(uuid4())
    draft_album_id = str(uuid4())
    db_session.execute(
        text(
            """
            INSERT INTO albums (id, owner_composer_id, title, status, likes_count, comments_count)
            VALUES (:id, :owner_composer_id, :title, :status, 0, 0)
            """
        ),
        {
            "id": published_album_id,
            "owner_composer_id": composer_profile_id,
            "title": "Published Album",
            "status": "published",
        },
    )
    db_session.execute(
        text(
            """
            INSERT INTO albums (id, owner_composer_id, title, status, likes_count, comments_count)
            VALUES (:id, :owner_composer_id, :title, :status, 0, 0)
            """
        ),
        {
            "id": draft_album_id,
            "owner_composer_id": composer_profile_id,
            "title": "Draft Album",
            "status": "draft",
        },
    )
    db_session.commit()

    repository = SqlAlchemyCatalogRepository(db_session)
    result = repository.list_albums(
        AlbumListFilter(
            status="published",
            owner_composer_id=UUID(composer_profile_id),
            include_unpublished=True,
        )
    )

    assert len(result) == 1
    assert result[0].id == UUID(published_album_id)
    assert result[0].status == "published"
