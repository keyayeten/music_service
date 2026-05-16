from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from backend.infrastructure.persistence.repositories.social import SqlAlchemySocialRepository


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


def _insert_published_track(db_session, title: str) -> UUID:
    track_id = uuid4()
    db_session.execute(
        text(
            """
            INSERT INTO tracks (id, title, status, duration_seconds, plays_count, likes_count, comments_count)
            VALUES (:id, :title, 'published', 180, 0, 0, 0)
            """
        ),
        {"id": track_id, "title": title},
    )
    db_session.commit()
    return track_id


@pytest.mark.integration
def test_like_idempotency_and_like_counter_update(db_session) -> None:
    user_id = _insert_user(db_session)
    track_id = _insert_published_track(db_session, "Stage5 Track")
    repository = SqlAlchemySocialRepository(db_session)

    inserted_first = repository.add_like(user_id=user_id, target_type="track", target_id=track_id)
    if inserted_first:
        repository.add_library_item_for_like(user_id=user_id, target_type="track", target_id=track_id)
        repository.update_target_counters(target_type="track", target_id=track_id, likes_delta=1)
    inserted_second = repository.add_like(user_id=user_id, target_type="track", target_id=track_id)
    if inserted_second:
        repository.update_target_counters(target_type="track", target_id=track_id, likes_delta=1)
    db_session.commit()

    assert inserted_first is True
    assert inserted_second is False
    counters = repository.get_target("track", track_id)
    assert counters is not None
    assert counters.likes_count == 1
    library_rows = db_session.execute(
        text(
            """
            SELECT COUNT(*) FROM library_items
            WHERE user_id = :user_id AND item_type = 'track' AND item_id = :item_id AND section = 'favorites'
            """
        ),
        {"user_id": user_id, "item_id": track_id},
    ).scalar_one()
    assert library_rows == 1


@pytest.mark.integration
def test_like_counter_non_negative_on_unlike(db_session) -> None:
    _insert_user(db_session)
    track_id = _insert_published_track(db_session, "Stage5 Track Unlike")
    repository = SqlAlchemySocialRepository(db_session)

    updated = repository.update_target_counters(target_type="track", target_id=track_id, likes_delta=-1)
    db_session.commit()

    assert updated is not None
    assert updated.likes_count == 0


@pytest.mark.integration
def test_comment_reply_parent_relation_and_counter_update(db_session) -> None:
    user_id = _insert_user(db_session)
    track_id = _insert_published_track(db_session, "Stage5 Track Comments")
    repository = SqlAlchemySocialRepository(db_session)

    parent = repository.create_comment(
        user_id=user_id,
        target_type="track",
        target_id=track_id,
        parent_comment_id=None,
        body="Root comment",
        status="visible",
    )
    repository.update_target_counters(target_type="track", target_id=track_id, comments_delta=1)
    reply = repository.create_comment(
        user_id=user_id,
        target_type="track",
        target_id=track_id,
        parent_comment_id=parent.id,
        body="Reply comment",
        status="visible",
    )
    repository.update_target_counters(target_type="track", target_id=track_id, comments_delta=1)
    db_session.commit()

    assert reply.parent_comment_id == parent.id
    counters = repository.get_target("track", track_id)
    assert counters is not None
    assert counters.comments_count == 2
    listed = repository.list_comments(target_type="track", target_id=track_id, limit=20, offset=0)
    assert {item.id for item in listed} == {parent.id, reply.id}


@pytest.mark.integration
def test_like_and_counter_changes_are_transactional(db_session) -> None:
    user_id = _insert_user(db_session)
    track_id = _insert_published_track(db_session, "Stage5 Transactional Track")
    repository = SqlAlchemySocialRepository(db_session)

    repository.add_like(user_id=user_id, target_type="track", target_id=track_id)
    repository.update_target_counters(target_type="track", target_id=track_id, likes_delta=1)
    db_session.rollback()

    like_count = db_session.execute(
        text(
            """
            SELECT COUNT(*) FROM likes
            WHERE user_id = :user_id AND target_type = 'track' AND target_id = :target_id
            """
        ),
        {"user_id": user_id, "target_id": track_id},
    ).scalar_one()
    persisted_counter = db_session.execute(
        text("SELECT likes_count FROM tracks WHERE id = :track_id"),
        {"track_id": track_id},
    ).scalar_one()

    assert like_count == 0
    assert persisted_counter == 0


@pytest.mark.integration
def test_unlike_removes_synced_library_item(db_session) -> None:
    user_id = _insert_user(db_session)
    track_id = _insert_published_track(db_session, "Stage5 Track Library Sync")
    repository = SqlAlchemySocialRepository(db_session)

    inserted = repository.add_like(user_id=user_id, target_type="track", target_id=track_id)
    if inserted:
        repository.add_library_item_for_like(user_id=user_id, target_type="track", target_id=track_id)
        repository.update_target_counters(target_type="track", target_id=track_id, likes_delta=1)
    removed = repository.remove_like(user_id=user_id, target_type="track", target_id=track_id)
    if removed:
        repository.remove_library_item_for_like(user_id=user_id, target_type="track", target_id=track_id)
        repository.update_target_counters(target_type="track", target_id=track_id, likes_delta=-1)
    db_session.commit()

    library_rows = db_session.execute(
        text(
            """
            SELECT COUNT(*) FROM library_items
            WHERE user_id = :user_id AND item_type = 'track' AND item_id = :item_id
            """
        ),
        {"user_id": user_id, "item_id": track_id},
    ).scalar_one()
    assert library_rows == 0
