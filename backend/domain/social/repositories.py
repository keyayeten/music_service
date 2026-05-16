from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

SOCIAL_TARGET_TYPES = {"track", "album", "playlist"}
COMMENT_STATUSES = {"visible", "hidden", "deleted", "pending_review"}


@dataclass(frozen=True)
class SocialTargetReadModel:
    target_type: str
    target_id: UUID
    likes_count: int
    comments_count: int


@dataclass(frozen=True)
class CommentReadModel:
    id: UUID
    user_id: UUID
    target_type: str
    target_id: UUID
    parent_comment_id: UUID | None
    body: str
    status: str
    created_at: datetime


class SocialRepository(Protocol):
    async def get_target(self, target_type: str, target_id: UUID) -> SocialTargetReadModel | None:
        """Return interactable target projection."""

    async def add_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> bool:
        """Create like record, returns True when inserted."""

    async def remove_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> bool:
        """Delete like record, returns True when removed."""

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
        """Create comment and return projection."""

    async def get_comment_by_id(self, comment_id: UUID) -> CommentReadModel | None:
        """Return comment projection by id."""

    async def list_comments(
        self,
        *,
        target_type: str,
        target_id: UUID,
        limit: int,
        offset: int,
    ) -> list[CommentReadModel]:
        """List visible comments for target ordered by creation date."""

    async def update_target_counters(
        self,
        *,
        target_type: str,
        target_id: UUID,
        likes_delta: int = 0,
        comments_delta: int = 0,
    ) -> SocialTargetReadModel | None:
        """Apply denormalized counter updates with non-negative guard."""

    async def add_library_item_for_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> None:
        """Synchronize like into library sections idempotently."""

    async def remove_library_item_for_like(self, *, user_id: UUID, target_type: str, target_id: UUID) -> None:
        """Synchronize unlike removal from library sections idempotently."""
