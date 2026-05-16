from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class TrackAuthorReadModel:
    composer_profile_id: UUID
    contribution_role: str
    position: int


@dataclass(frozen=True)
class TrackReadModel:
    id: UUID
    title: str
    description: str | None
    status: str
    duration_seconds: int
    plays_count: int
    likes_count: int
    comments_count: int
    published_at: datetime | None
    created_at: datetime
    authors: list[TrackAuthorReadModel]
    genre_codes: list[str]


@dataclass(frozen=True)
class AlbumTrackReadModel:
    track_id: UUID
    position: int


@dataclass(frozen=True)
class AlbumReadModel:
    id: UUID
    owner_composer_id: UUID
    title: str
    description: str | None
    status: str
    release_date: date | None
    likes_count: int
    comments_count: int
    created_at: datetime
    track_items: list[AlbumTrackReadModel]


@dataclass(frozen=True)
class TrackListFilter:
    status: str | None = None
    genre_code: str | None = None
    author_id: UUID | None = None
    include_unpublished: bool = False


@dataclass(frozen=True)
class AlbumListFilter:
    status: str | None = None
    owner_composer_id: UUID | None = None
    include_unpublished: bool = False


class CatalogRepository(Protocol):
    def get_user_role_codes(self, user_id: UUID) -> list[str]:
        """List role codes assigned to user."""

    def get_composer_profile_id_by_user_id(self, user_id: UUID) -> UUID | None:
        """Resolve composer profile id for identity user."""

    def create_track(
        self,
        *,
        title: str,
        description: str | None,
        duration_seconds: int,
        primary_author_id: UUID,
    ) -> TrackReadModel:
        """Create draft track and assign the primary author."""

    def update_track(
        self,
        *,
        track_id: UUID,
        title: str,
        description: str | None,
        duration_seconds: int,
    ) -> TrackReadModel | None:
        """Update mutable track fields."""

    def replace_track_authors(self, track_id: UUID, authors: list[TrackAuthorReadModel]) -> None:
        """Replace all track author records."""

    def set_track_status(self, track_id: UUID, status: str, published_at: datetime | None) -> TrackReadModel | None:
        """Set status and publication timestamp."""

    def get_track_by_id(self, track_id: UUID) -> TrackReadModel | None:
        """Return track projection with related authors/genres."""

    def list_tracks(self, filters: TrackListFilter) -> list[TrackReadModel]:
        """Return track projections by filter."""

    def create_album(
        self,
        *,
        owner_composer_id: UUID,
        title: str,
        description: str | None,
        release_date: date | None,
    ) -> AlbumReadModel:
        """Create draft album."""

    def update_album(
        self,
        *,
        album_id: UUID,
        title: str,
        description: str | None,
        release_date: date | None,
    ) -> AlbumReadModel | None:
        """Update album fields."""

    def replace_album_tracks(self, album_id: UUID, track_ids: list[UUID]) -> None:
        """Replace album track composition preserving provided order."""

    def set_album_status(self, album_id: UUID, status: str) -> AlbumReadModel | None:
        """Set album publication status."""

    def get_album_by_id(self, album_id: UUID) -> AlbumReadModel | None:
        """Return album with ordered track items."""

    def list_albums(self, filters: AlbumListFilter) -> list[AlbumReadModel]:
        """Return album projections by filter."""
