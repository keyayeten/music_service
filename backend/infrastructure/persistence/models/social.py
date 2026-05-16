from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.persistence.models.base import Base

SOCIAL_TARGET_TYPES = ("track", "album", "playlist")
COMMENT_STATUSES = ("visible", "hidden", "deleted", "pending_review")


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint(f"target_type IN {SOCIAL_TARGET_TYPES}", name="ck_comments_target_type"),
        CheckConstraint(f"status IN {COMMENT_STATUSES}", name="ck_comments_status"),
        Index("ix_comments_target_created", "target_type", "target_id", "created_at"),
        Index(
            "ix_comments_visible_target_created",
            "target_type",
            "target_id",
            "created_at",
            postgresql_where=text("status = 'visible'"),
        ),
        Index("ix_comments_user_created", "user_id", "created_at"),
        Index("ix_comments_parent", "parent_comment_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[UUID] = mapped_column(nullable=False)
    parent_comment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comments.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="visible", server_default="visible")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_likes_user_target"),
        CheckConstraint(f"target_type IN {SOCIAL_TARGET_TYPES}", name="ck_likes_target_type"),
        Index("ix_likes_target_created", "target_type", "target_id", "created_at"),
        Index("ix_likes_user_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
