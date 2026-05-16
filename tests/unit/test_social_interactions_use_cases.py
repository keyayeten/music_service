from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from backend.application.social.use_cases.interactions import SocialInteractionUseCases
from backend.domain.common.exceptions import ValidationError
from backend.domain.social.repositories import CommentReadModel, SocialTargetReadModel
from tests.async_tools import run_async


class _FakeSocialRepository:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.target_id = uuid4()
        self.other_target_id = uuid4()
        self.target = SocialTargetReadModel(
            target_type="track",
            target_id=self.target_id,
            likes_count=0,
            comments_count=0,
        )
        self.likes: set[tuple[UUID, str, UUID]] = set()
        self.comments: dict[UUID, CommentReadModel] = {}
        self.library_items: set[tuple[UUID, str, UUID, str]] = set()

    async def get_target(self, target_type: str, target_id: UUID) -> SocialTargetReadModel | None:
        if target_type == self.target.target_type and target_id == self.target.target_id:
            return self.target
        return None

    async def add_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> bool:
        marker = (user_id, target_type, target_id)
        if marker in self.likes:
            return False
        self.likes.add(marker)
        return True

    async def remove_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> bool:
        marker = (user_id, target_type, target_id)
        if marker not in self.likes:
            return False
        self.likes.remove(marker)
        return True

    async def create_comment(
        self,
        *,
        user_id: UUID,
        target_type: str,
        target_id: UUID,
        parent_comment_id: UUID | None,
        body: str,
        status: str,
    ) -> CommentReadModel:
        created = CommentReadModel(
            id=uuid4(),
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            parent_comment_id=parent_comment_id,
            body=body,
            status=status,
            created_at=datetime.now(UTC),
        )
        self.comments[created.id] = created
        return created

    async def get_comment_by_id(self, comment_id: UUID) -> CommentReadModel | None:
        return self.comments.get(comment_id)

    async def list_comments(
        self,
        *,
        target_type: str,
        target_id: UUID,
        limit: int,
        offset: int,
    ) -> list[CommentReadModel]:
        items = [
            item
            for item in self.comments.values()
            if item.target_type == target_type and item.target_id == target_id and item.status == "visible"
        ]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[offset : offset + limit]

    async def update_target_counters(
        self,
        *,
        target_type: str,
        target_id: UUID,
        likes_delta: int = 0,
        comments_delta: int = 0,
    ) -> SocialTargetReadModel | None:
        current = await self.get_target(target_type, target_id)
        if current is None:
            return None
        self.target = SocialTargetReadModel(
            target_type=current.target_type,
            target_id=current.target_id,
            likes_count=max(0, current.likes_count + likes_delta),
            comments_count=max(0, current.comments_count + comments_delta),
        )
        return self.target

    async def add_library_item_for_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> None:
        section = "favorites" if target_type == "track" else "albums" if target_type == "album" else "playlists"
        self.library_items.add((user_id, target_type, target_id, section))

    async def remove_library_item_for_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> None:
        section = "favorites" if target_type == "track" else "albums" if target_type == "album" else "playlists"
        self.library_items.discard((user_id, target_type, target_id, section))


@pytest.mark.unit
def test_like_is_idempotent_and_counter_updates_once() -> None:
    repository = _FakeSocialRepository()
    use_cases = SocialInteractionUseCases(repository=repository)

    first = run_async(use_cases.like(repository.user_id, target_type="track", target_id=repository.target_id))
    second = run_async(use_cases.like(repository.user_id, target_type="track", target_id=repository.target_id))

    assert first.likes_count == 1
    assert second.likes_count == 1
    assert (repository.user_id, "track", repository.target_id, "favorites") in repository.library_items


@pytest.mark.unit
def test_unlike_never_makes_counter_negative() -> None:
    repository = _FakeSocialRepository()
    use_cases = SocialInteractionUseCases(repository=repository)

    result = run_async(use_cases.unlike(repository.user_id, target_type="track", target_id=repository.target_id))

    assert result.likes_count == 0


@pytest.mark.unit
def test_comment_reply_requires_parent_from_same_target() -> None:
    repository = _FakeSocialRepository()
    parent = CommentReadModel(
        id=uuid4(),
        user_id=repository.user_id,
        target_type="track",
        target_id=repository.other_target_id,
        parent_comment_id=None,
        body="first",
        status="visible",
        created_at=datetime.now(UTC),
    )
    repository.comments[parent.id] = parent
    use_cases = SocialInteractionUseCases(repository=repository)

    with pytest.raises(ValidationError):
        run_async(use_cases.comment(
            repository.user_id,
            target_type="track",
            target_id=repository.target_id,
            body="reply",
            parent_comment_id=parent.id,
        ))


@pytest.mark.unit
def test_comment_increments_comments_counter() -> None:
    repository = _FakeSocialRepository()
    use_cases = SocialInteractionUseCases(repository=repository)

    comment, counters = run_async(
        use_cases.comment(
            repository.user_id,
            target_type="track",
            target_id=repository.target_id,
            body="Nice release",
            parent_comment_id=None,
        )
    )

    assert comment.body == "Nice release"
    assert counters.comments_count == 1


@pytest.mark.unit
def test_get_and_list_comments_return_only_target_comments() -> None:
    repository = _FakeSocialRepository()
    use_cases = SocialInteractionUseCases(repository=repository)
    comment, _ = run_async(
        use_cases.comment(
            repository.user_id,
            target_type="track",
            target_id=repository.target_id,
            body="Visible comment",
            parent_comment_id=None,
        )
    )

    got = run_async(use_cases.get_comment(target_type="track", target_id=repository.target_id, comment_id=comment.id))
    listed = run_async(use_cases.list_comments(target_type="track", target_id=repository.target_id, limit=20, offset=0))

    assert got.id == comment.id
    assert [item.id for item in listed] == [comment.id]
