from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.persistence.models.base import Base

PLAYLIST_VISIBILITIES = ("private", "unlisted", "public")
LIBRARY_ITEM_TYPES = ("track", "album", "playlist")
LIBRARY_SECTIONS = ("favorites", "albums", "playlists")


class Playlist(Base):
    __tablename__ = "playlists"
    __table_args__ = (
        CheckConstraint(f"visibility IN {PLAYLIST_VISIBILITIES}", name="ck_playlists_visibility"),
        Index("ix_playlists_owner_created", "owner_user_id", "created_at"),
        Index("ix_playlists_visibility_likes", "visibility", "likes_count"),
        Index("ix_playlists_visibility_created", "visibility", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="private", server_default="private")
    likes_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    comments_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"
    __table_args__ = (
        UniqueConstraint("playlist_id", "position", name="uq_playlist_tracks_playlist_position"),
        CheckConstraint("position > 0", name="ck_playlist_tracks_position_positive"),
        Index("ix_playlist_tracks_playlist_position", "playlist_id", "position"),
    )

    playlist_id: Mapped[UUID] = mapped_column(ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True)
    track_id: Mapped[UUID] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True)
    added_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LibraryItem(Base):
    __tablename__ = "library_items"
    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "item_id", name="uq_library_items_user_item"),
        CheckConstraint(f"item_type IN {LIBRARY_ITEM_TYPES}", name="ck_library_items_item_type"),
        CheckConstraint(f"section IN {LIBRARY_SECTIONS}", name="ck_library_items_section"),
        Index("ix_library_items_user_section_created", "user_id", "section", "created_at"),
        Index("ix_library_items_item", "item_type", "item_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    item_id: Mapped[UUID] = mapped_column(nullable=False)
    section: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
