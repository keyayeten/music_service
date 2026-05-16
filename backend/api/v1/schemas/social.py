from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LikeResponse(BaseModel):
    target_type: str
    target_id: str
    likes_count: int
    comments_count: int


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    parent_comment_id: str | None = None


class CommentResponse(BaseModel):
    id: str
    user_id: str
    target_type: str
    target_id: str
    parent_comment_id: str | None
    body: str
    status: str
    created_at: datetime


class CommentWithCountersResponse(BaseModel):
    comment: CommentResponse
    counters: LikeResponse


class ListCommentsResponse(BaseModel):
    items: list[CommentResponse]
