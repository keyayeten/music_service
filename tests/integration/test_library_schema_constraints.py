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


def _insert_track(db_session, title: str) -> str:
    track_id = str(uuid4())
    db_session.execute(
        text(
            """
            INSERT INTO tracks (id, title, status, duration_seconds, plays_count, likes_count, comments_count)
            VALUES (:id, :title, 'draft', 120, 0, 0, 0)
            """
        ),
        {"id": track_id, "title": title},
    )
    db_session.commit()
    return track_id


@pytest.mark.integration
def test_playlist_tracks_unique_position_constraint(db_session) -> None:
    owner_id = _insert_user(db_session)
    first_track_id = _insert_track(db_session, "Track One")
    second_track_id = _insert_track(db_session, "Track Two")
    playlist_id = str(uuid4())
    db_session.execute(
        text(
            """
            INSERT INTO playlists (id, owner_user_id, title, visibility, likes_count, comments_count)
            VALUES (:id, :owner_user_id, :title, 'private', 0, 0)
            """
        ),
        {"id": playlist_id, "owner_user_id": owner_id, "title": "Stage4 Playlist"},
    )
    db_session.execute(
        text(
            """
            INSERT INTO playlist_tracks (playlist_id, track_id, added_by_user_id, position)
            VALUES (:playlist_id, :track_id, :added_by_user_id, :position)
            """
        ),
        {"playlist_id": playlist_id, "track_id": first_track_id, "added_by_user_id": owner_id, "position": 1},
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO playlist_tracks (playlist_id, track_id, added_by_user_id, position)
                VALUES (:playlist_id, :track_id, :added_by_user_id, :position)
                """
            ),
            {"playlist_id": playlist_id, "track_id": second_track_id, "added_by_user_id": owner_id, "position": 1},
        )
        db_session.commit()
    db_session.rollback()


@pytest.mark.integration
def test_playlist_tracks_disallow_duplicate_track_in_playlist(db_session) -> None:
    owner_id = _insert_user(db_session)
    track_id = _insert_track(db_session, "Track Duplicate")
    playlist_id = str(uuid4())
    db_session.execute(
        text(
            """
            INSERT INTO playlists (id, owner_user_id, title, visibility, likes_count, comments_count)
            VALUES (:id, :owner_user_id, :title, 'private', 0, 0)
            """
        ),
        {"id": playlist_id, "owner_user_id": owner_id, "title": "Stage4 Playlist Duplicate"},
    )
    db_session.execute(
        text(
            """
            INSERT INTO playlist_tracks (playlist_id, track_id, added_by_user_id, position)
            VALUES (:playlist_id, :track_id, :added_by_user_id, :position)
            """
        ),
        {"playlist_id": playlist_id, "track_id": track_id, "added_by_user_id": owner_id, "position": 1},
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO playlist_tracks (playlist_id, track_id, added_by_user_id, position)
                VALUES (:playlist_id, :track_id, :added_by_user_id, :position)
                """
            ),
            {"playlist_id": playlist_id, "track_id": track_id, "added_by_user_id": owner_id, "position": 2},
        )
        db_session.commit()
    db_session.rollback()


@pytest.mark.integration
def test_library_items_unique_user_item_constraint(db_session) -> None:
    owner_id = _insert_user(db_session)
    track_id = _insert_track(db_session, "Track Library")
    db_session.execute(
        text(
            """
            INSERT INTO library_items (id, user_id, item_type, item_id, section)
            VALUES (:id, :user_id, 'track', :item_id, 'favorites')
            """
        ),
        {"id": str(uuid4()), "user_id": owner_id, "item_id": track_id},
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO library_items (id, user_id, item_type, item_id, section)
                VALUES (:id, :user_id, 'track', :item_id, 'favorites')
                """
            ),
            {"id": str(uuid4()), "user_id": owner_id, "item_id": track_id},
        )
        db_session.commit()
    db_session.rollback()
