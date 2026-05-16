from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.api.deps import get_current_identity_user, get_db_session, get_discovery_use_cases, get_social_interaction_use_cases
from backend.api.v1.schemas.social import (
    CommentResponse,
    CommentWithCountersResponse,
    CreateCommentRequest,
    LikeResponse,
    ListCommentsResponse,
)
from backend.application.discovery.use_cases.events_and_recommendations import DiscoveryUseCases
from backend.application.social.use_cases.interactions import SocialInteractionUseCases
from backend.domain.common.exceptions import ValidationError
from backend.domain.identity.repositories import IdentityUserReadModel
from backend.domain.social.repositories import CommentReadModel, SocialTargetReadModel

router = APIRouter(prefix="/social", tags=["social"])


@router.post("/{target_type}/{target_id}/like", response_model=LikeResponse)
def like_target(
    target_type: str,
    target_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: SocialInteractionUseCases = Depends(get_social_interaction_use_cases),
    discovery_use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
    db_session: Session = Depends(get_db_session),
) -> LikeResponse:
    try:
        result = use_cases.like(user.id, target_type=target_type, target_id=target_id)
        discovery_use_cases.record_like_events(
            user.id,
            target_type=target_type,
            target_id=target_id,
        )
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return _to_like_response(result)


@router.delete("/{target_type}/{target_id}/like", response_model=LikeResponse)
def unlike_target(
    target_type: str,
    target_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: SocialInteractionUseCases = Depends(get_social_interaction_use_cases),
    db_session: Session = Depends(get_db_session),
) -> LikeResponse:
    try:
        result = use_cases.unlike(user.id, target_type=target_type, target_id=target_id)
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return _to_like_response(result)


@router.post("/{target_type}/{target_id}/comments", response_model=CommentWithCountersResponse)
def comment_target(
    target_type: str,
    target_id: UUID,
    payload: CreateCommentRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: SocialInteractionUseCases = Depends(get_social_interaction_use_cases),
    discovery_use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
    db_session: Session = Depends(get_db_session),
) -> CommentWithCountersResponse:
    try:
        parent_comment_id = UUID(payload.parent_comment_id) if payload.parent_comment_id else None
        comment, counters = use_cases.comment(
            user.id,
            target_type=target_type,
            target_id=target_id,
            body=payload.body,
            parent_comment_id=parent_comment_id,
        )
        discovery_use_cases.record_comment_events(
            user.id,
            target_type=target_type,
            target_id=target_id,
        )
        db_session.commit()
    except ValueError as exc:
        db_session.rollback()
        raise _http_error(
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
            "Parent comment id should be a valid UUID value.",
        ) from exc
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return CommentWithCountersResponse(
        comment=_to_comment_response(comment),
        counters=_to_like_response(counters),
    )


@router.get("/{target_type}/{target_id}/comments", response_model=ListCommentsResponse)
def list_comments(
    target_type: str,
    target_id: UUID,
    limit: int = Query(default=20),
    offset: int = Query(default=0),
    _user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: SocialInteractionUseCases = Depends(get_social_interaction_use_cases),
) -> ListCommentsResponse:
    try:
        items = use_cases.list_comments(
            target_type=target_type,
            target_id=target_id,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return ListCommentsResponse(items=[_to_comment_response(item) for item in items])


@router.get("/{target_type}/{target_id}/comments/{comment_id}", response_model=CommentResponse)
def get_comment(
    target_type: str,
    target_id: UUID,
    comment_id: UUID,
    _user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: SocialInteractionUseCases = Depends(get_social_interaction_use_cases),
) -> CommentResponse:
    try:
        item = use_cases.get_comment(
            target_type=target_type,
            target_id=target_id,
            comment_id=comment_id,
        )
    except ValidationError as exc:
        raise _http_error(status.HTTP_404_NOT_FOUND, "not_found", exc.message) from exc
    return _to_comment_response(item)


def _to_like_response(item: SocialTargetReadModel) -> LikeResponse:
    return LikeResponse(
        target_type=item.target_type,
        target_id=str(item.target_id),
        likes_count=item.likes_count,
        comments_count=item.comments_count,
    )


def _to_comment_response(item: CommentReadModel) -> CommentResponse:
    return CommentResponse(
        id=str(item.id),
        user_id=str(item.user_id),
        target_type=item.target_type,
        target_id=str(item.target_id),
        parent_comment_id=str(item.parent_comment_id) if item.parent_comment_id else None,
        body=item.body,
        status=item.status,
        created_at=item.created_at,
    )


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
