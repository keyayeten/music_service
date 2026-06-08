from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

PLAYLIST_VISIBILITIES = {"private", "unlisted", "public"}
LIBRARY_ITEM_TYPES = {"track", "album", "playlist"}
LIBRARY_SECTIONS = {"favorites", "albums", "playlists"}


@dataclass(frozen=True)
class PlaylistTrackItemReadModel:
    track_id: UUID
    added_by_user_id: UUID
    position: int
    added_at: datetime


@dataclass(frozen=True)
class PlaylistReadModel:
    id: UUID
    owner_user_id: UUID
    title: str
    description: str | None
    visibility: str
    likes_count: int
    comments_count: int
    created_at: datetime
    track_items: list[PlaylistTrackItemReadModel]


@dataclass(frozen=True)
class LibraryItemReadModel:
    id: UUID
    user_id: UUID
    item_type: str
    item_id: UUID
    section: str
    created_at: datetime


@dataclass(frozen=True)
class PlaylistListFilter:
    owner_user_id: UUID | None = None
    visibility: str | None = None
    include_unlisted: bool = False
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class LibraryListFilter:
    user_id: UUID
    section: str | None = None
    item_type: str | None = None
    limit: int = 20
    offset: int = 0


class LibraryRepository(Protocol):
    async def create_playlist(
        self,
        *,
        owner_user_id: UUID,
        title: str,
        description: str | None,
        visibility: str,
    ) -> PlaylistReadModel:
        """Create a playlist."""

    async def update_playlist(
        self,
        *,
        playlist_id: UUID,
        title: str,
        description: str | None,
        visibility: str,
    ) -> PlaylistReadModel | None:
        """Update mutable playlist fields."""

    async def delete_playlist(self, playlist_id: UUID) -> bool:
        """Delete playlist and associated tracks."""

    async def get_playlist_by_id(self, playlist_id: UUID) -> PlaylistReadModel | None:
        """Return playlist projection with ordered tracks."""

    async def list_playlists(self, filters: PlaylistListFilter) -> list[PlaylistReadModel]:
        """Return playlist projections by filters."""

    async def add_playlist_track(
        self,
        *,
        playlist_id: UUID,
        track_id: UUID,
        added_by_user_id: UUID,
        position: int,
    ) -> None:
        """Append track record at target position."""

    async def remove_playlist_track(self, *, playlist_id: UUID, track_id: UUID) -> bool:
        """Remove track from playlist."""

    async def replace_playlist_tracks(
        self, playlist_id: UUID, tracks: list[PlaylistTrackItemReadModel]
    ) -> None:
        """Replace all playlist tracks preserving order."""

    async def get_playlist_track_count(self, playlist_id: UUID) -> int:
        """Count tracks in playlist."""

    async def track_exists(self, track_id: UUID) -> bool:
        """Check whether catalog track exists."""

    async def add_library_item(
        self,
        *,
        user_id: UUID,
        item_type: str,
        item_id: UUID,
        section: str,
    ) -> LibraryItemReadModel:
        """Create library item."""

    async def remove_library_item(self, *, user_id: UUID, item_type: str, item_id: UUID) -> bool:
        """Delete user library item."""

    async def list_library_items(self, filters: LibraryListFilter) -> list[LibraryItemReadModel]:
        """List library items by filter."""

    async def item_exists(self, item_type: str, item_id: UUID) -> bool:
        """Check whether referenced entity exists for polymorphic library item."""
