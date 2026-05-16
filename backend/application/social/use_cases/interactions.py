from __future__ import annotations

from uuid import UUID

from backend.domain.common.exceptions import ValidationError
from backend.domain.social.repositories import SOCIAL_TARGET_TYPES, CommentReadModel, SocialRepository, SocialTargetReadModel


class SocialInteractionUseCases:
    def __init__(self, repository: SocialRepository) -> None:
        self._repository = repository

    def like(self, actor_user_id: UUID, *, target_type: str, target_id: UUID) -> SocialTargetReadModel:
        normalized_target_type = _normalize_target_type(target_type)
        self._require_target(normalized_target_type, target_id)
        inserted = self._repository.add_like(
            user_id=actor_user_id,
            target_type=normalized_target_type,
            target_id=target_id,
        )
        if inserted:
            self._repository.add_library_item_for_like(
                user_id=actor_user_id,
                target_type=normalized_target_type,
                target_id=target_id,
            )
            updated = self._repository.update_target_counters(
                target_type=normalized_target_type,
                target_id=target_id,
                likes_delta=1,
            )
        else:
            updated = self._repository.get_target(normalized_target_type, target_id)
        if updated is None:
            raise ValidationError("Target is not found.")
        return updated

    def unlike(self, actor_user_id: UUID, *, target_type: str, target_id: UUID) -> SocialTargetReadModel:
        normalized_target_type = _normalize_target_type(target_type)
        self._require_target(normalized_target_type, target_id)
        removed = self._repository.remove_like(
            user_id=actor_user_id,
            target_type=normalized_target_type,
            target_id=target_id,
        )
        if removed:
            self._repository.remove_library_item_for_like(
                user_id=actor_user_id,
                target_type=normalized_target_type,
                target_id=target_id,
            )
            updated = self._repository.update_target_counters(
                target_type=normalized_target_type,
                target_id=target_id,
                likes_delta=-1,
            )
        else:
            updated = self._repository.get_target(normalized_target_type, target_id)
        if updated is None:
            raise ValidationError("Target is not found.")
        return updated

    def comment(
        self,
        actor_user_id: UUID,
        *,
        target_type: str,
        target_id: UUID,
        body: str,
        parent_comment_id: UUID | None,
    ) -> tuple[CommentReadModel, SocialTargetReadModel]:
        normalized_target_type = _normalize_target_type(target_type)
        normalized_body = _normalize_comment_body(body)
        self._require_target(normalized_target_type, target_id)
        if parent_comment_id is not None:
            parent = self._repository.get_comment_by_id(parent_comment_id)
            if parent is None:
                raise ValidationError("Parent comment is not found.")
            if parent.target_type != normalized_target_type or parent.target_id != target_id:
                raise ValidationError("Parent comment should belong to the same target.")
        comment = self._repository.create_comment(
            user_id=actor_user_id,
            target_type=normalized_target_type,
            target_id=target_id,
            parent_comment_id=parent_comment_id,
            body=normalized_body,
            status="visible",
        )
        updated = self._repository.update_target_counters(
            target_type=normalized_target_type,
            target_id=target_id,
            comments_delta=1,
        )
        if updated is None:
            raise ValidationError("Target is not found.")
        return comment, updated

    def get_comment(self, *, target_type: str, target_id: UUID, comment_id: UUID) -> CommentReadModel:
        normalized_target_type = _normalize_target_type(target_type)
        self._require_target(normalized_target_type, target_id)
        comment = self._repository.get_comment_by_id(comment_id)
        if comment is None:
            raise ValidationError("Comment is not found.")
        if comment.target_type != normalized_target_type or comment.target_id != target_id:
            raise ValidationError("Comment is not found for target.")
        if comment.status != "visible":
            raise ValidationError("Comment is not visible.")
        return comment

    def list_comments(self, *, target_type: str, target_id: UUID, limit: int, offset: int) -> list[CommentReadModel]:
        normalized_target_type = _normalize_target_type(target_type)
        self._require_target(normalized_target_type, target_id)
        if limit < 1 or limit > 100:
            raise ValidationError("Limit should be between 1 and 100.")
        if offset < 0:
            raise ValidationError("Offset should be a non-negative number.")
        return self._repository.list_comments(
            target_type=normalized_target_type,
            target_id=target_id,
            limit=limit,
            offset=offset,
        )

    def _require_target(self, target_type: str, target_id: UUID) -> SocialTargetReadModel:
        target = self._repository.get_target(target_type, target_id)
        if target is None:
            raise ValidationError("Target is not found.")
        return target


def _normalize_target_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in SOCIAL_TARGET_TYPES:
        raise ValidationError("Unsupported target type.")
    return normalized


def _normalize_comment_body(value: str) -> str:
    normalized = value.strip()
    if len(normalized) < 1:
        raise ValidationError("Comment body should not be empty.")
    if len(normalized) > 4000:
        raise ValidationError("Comment body should contain at most 4000 characters.")
    return normalized
