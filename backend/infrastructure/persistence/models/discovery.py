from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.persistence.models.base import Base

TRACK_EVENT_TYPES = ("view", "external_click", "like", "save", "comment", "playlist_add")


class UserTrackEvent(Base):
    __tablename__ = "user_track_events"
    __table_args__ = (
        CheckConstraint(f"event_type IN {TRACK_EVENT_TYPES}", name="ck_user_track_events_event_type"),
        Index("ix_user_track_events_user_created", "user_id", "created_at"),
        Index("ix_user_track_events_track_created", "track_id", "created_at"),
        Index("ix_user_track_events_type_created", "event_type", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    track_id: Mapped[UUID] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExternalLinkClick(Base):
    __tablename__ = "external_link_clicks"
    __table_args__ = (
        Index("ix_external_link_clicks_user_created", "user_id", "created_at"),
        Index("ix_external_link_clicks_link_created", "external_link_id", "created_at"),
        Index("ix_external_link_clicks_track_created", "track_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    external_link_id: Mapped[UUID] = mapped_column(ForeignKey("external_links.id", ondelete="CASCADE"), nullable=False)
    track_id: Mapped[UUID] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    click_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
