from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
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

TRACK_STATUSES = ("draft", "pending_review", "published", "rejected", "hidden")
ALBUM_STATUSES = ("draft", "pending_review", "published", "rejected", "hidden")
ENTITY_TYPES = ("track", "album", "playlist")
MUSIC_SERVICES = (
    "spotify",
    "apple_music",
    "youtube_music",
    "soundcloud",
    "bandcamp",
    "yandex_music",
    "vk_music",
    "other",
)


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        CheckConstraint(f"status IN {TRACK_STATUSES}", name="ck_tracks_status"),
        CheckConstraint("duration_seconds > 0", name="ck_tracks_duration_positive"),
        Index("ix_tracks_status_published_at", "status", "published_at"),
        Index("ix_tracks_likes_count", "likes_count"),
        Index("ix_tracks_plays_count", "plays_count"),
        Index(
            "ix_tracks_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", server_default="draft"
    )
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    plays_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    likes_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    comments_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrackAuthor(Base):
    __tablename__ = "track_authors"
    __table_args__ = (
        UniqueConstraint("track_id", "position", name="uq_track_authors_track_position"),
        CheckConstraint("position > 0", name="ck_track_authors_position_positive"),
        Index("ix_track_authors_composer", "composer_profile_id"),
    )

    track_id: Mapped[UUID] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )
    composer_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("composer_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    contribution_role: Mapped[str] = mapped_column(
        String(64), nullable=False, default="composer", server_default="composer"
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class Album(Base):
    __tablename__ = "albums"
    __table_args__ = (
        CheckConstraint(f"status IN {ALBUM_STATUSES}", name="ck_albums_status"),
        Index("ix_albums_owner_status_release", "owner_composer_id", "status", "release_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_composer_id: Mapped[UUID] = mapped_column(
        ForeignKey("composer_profiles.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", server_default="draft"
    )
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    likes_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    comments_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlbumTrack(Base):
    __tablename__ = "album_tracks"
    __table_args__ = (
        UniqueConstraint("album_id", "position", name="uq_album_tracks_album_position"),
        CheckConstraint("position > 0", name="ck_album_tracks_position_positive"),
        Index("ix_album_tracks_album_position", "album_id", "position"),
    )

    album_id: Mapped[UUID] = mapped_column(
        ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True
    )
    track_id: Mapped[UUID] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class ExternalLink(Base):
    __tablename__ = "external_links"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "service",
            "url",
            name="uq_external_links_entity_service_url",
        ),
        CheckConstraint(f"entity_type IN {ENTITY_TYPES}", name="ck_external_links_entity_type"),
        CheckConstraint(f"service IN {MUSIC_SERVICES}", name="ck_external_links_service"),
        Index("ix_external_links_entity", "entity_type", "entity_id"),
        Index("ix_external_links_service", "service"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    service: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TrackGenre(Base):
    __tablename__ = "track_genres"
    __table_args__ = (Index("ix_track_genres_genre", "genre_id"),)

    track_id: Mapped[UUID] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[UUID] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EntityTag(Base):
    __tablename__ = "entity_tags"
    __table_args__ = (
        UniqueConstraint("tag_id", "entity_type", "entity_id", name="uq_entity_tags_tag_entity"),
        CheckConstraint(f"entity_type IN {ENTITY_TYPES}", name="ck_entity_tags_entity_type"),
        Index("ix_entity_tags_entity", "entity_type", "entity_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tag_id: Mapped[UUID] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
