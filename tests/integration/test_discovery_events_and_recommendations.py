from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from backend.application.discovery.use_cases.events_and_recommendations import DiscoveryUseCases
from backend.infrastructure.persistence.repositories.discovery import SqlAlchemyDiscoveryRepository
from tests.async_tools import AsyncSessionAdapter, run_async


def _insert_user(db_session) -> UUID:
    user_id = uuid4()
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


def _insert_track(db_session, title: str, *, likes_count: int) -> UUID:
    track_id = uuid4()
    db_session.execute(
        text(
            """
            INSERT INTO tracks (id, title, status, duration_seconds, plays_count, likes_count, comments_count)
            VALUES (:id, :title, 'published', 180, 0, :likes_count, 0)
            """
        ),
        {"id": track_id, "title": title, "likes_count": likes_count},
    )
    db_session.commit()
    return track_id


def _insert_album_with_tracks(db_session, track_ids: list[UUID]) -> UUID:
    owner_user_id = _insert_user(db_session)
    composer_profile_id = uuid4()
    album_id = uuid4()
    db_session.execute(
        text(
            """
            INSERT INTO composer_profiles (id, user_id, display_name, bio, country_code, verified)
            VALUES (:id, :user_id, 'Discovery Composer', 'Bio', 'UA', false)
            """
        ),
        {"id": composer_profile_id, "user_id": owner_user_id},
    )
    db_session.execute(
        text(
            """
            INSERT INTO albums (id, owner_composer_id, title, status, likes_count, comments_count)
            VALUES (:id, :owner_composer_id, 'Discovery Album', 'published', 0, 0)
            """
        ),
        {"id": album_id, "owner_composer_id": composer_profile_id},
    )
    for index, track_id in enumerate(track_ids, start=1):
        db_session.execute(
            text(
                """
                INSERT INTO album_tracks (album_id, track_id, position)
                VALUES (:album_id, :track_id, :position)
                """
            ),
            {"album_id": album_id, "track_id": track_id, "position": index},
        )
    db_session.commit()
    return album_id


@pytest.mark.integration
def test_save_event_for_album_creates_track_events_with_relations(db_session) -> None:
    user_id = _insert_user(db_session)
    first_track_id = _insert_track(db_session, "Discovery Album Track A", likes_count=1)
    second_track_id = _insert_track(db_session, "Discovery Album Track B", likes_count=2)
    album_id = _insert_album_with_tracks(db_session, [first_track_id, second_track_id])
    repository = SqlAlchemyDiscoveryRepository(AsyncSessionAdapter(db_session))
    use_cases = DiscoveryUseCases(repository=repository)

    run_async(use_cases.record_save_events(user_id, item_type="album", item_id=album_id))
    db_session.commit()

    rows = db_session.execute(
        text(
            """
            SELECT track_id, event_type
            FROM user_track_events
            WHERE user_id = :user_id
            ORDER BY track_id
            """
        ),
        {"user_id": user_id},
    ).all()
    assert len(rows) == 2
    assert {row.track_id for row in rows} == {first_track_id, second_track_id}
    assert {row.event_type for row in rows} == {"save"}


@pytest.mark.integration
def test_top_recommendations_are_deterministic_by_score(db_session) -> None:
    repository = SqlAlchemyDiscoveryRepository(AsyncSessionAdapter(db_session))
    first_track_id = _insert_track(db_session, "Top A", likes_count=1000)
    second_track_id = _insert_track(db_session, "Top B", likes_count=900)

    result = run_async(repository.get_top_published_tracks(limit=200))
    ranked_ids = [item.track_id for item in result]

    assert first_track_id in ranked_ids
    assert second_track_id in ranked_ids
    assert ranked_ids.index(first_track_id) < ranked_ids.index(second_track_id)
