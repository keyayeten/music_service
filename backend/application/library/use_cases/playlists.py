from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.domain.library.repositories import (
    PLAYLIST_VISIBILITIES,
    LibraryRepository,
    PlaylistListFilter,
    PlaylistReadModel,
    PlaylistTrackItemReadModel,
)


class LibraryPlaylistUseCases:
    def __init__(self, repository: LibraryRepository) -> None:
        self._repository = repository

    async def create_playlist(
        self,
        actor_user_id: UUID,
        *,
        title: str,
        description: str | None,
        visibility: str,
    ) -> PlaylistReadModel:
        return await self._repository.create_playlist(
            owner_user_id=actor_user_id,
            title=_normalize_title(title),
            description=_normalize_optional_text(description),
            visibility=_normalize_visibility(visibility),
        )

    async def update_playlist(
        self,
        actor_user_id: UUID,
        *,
        playlist_id: UUID,
        title: str,
        description: str | None,
        visibility: str,
    ) -> PlaylistReadModel:
        await self._require_owned_playlist(actor_user_id, playlist_id)
        updated = await self._repository.update_playlist(
            playlist_id=playlist_id,
            title=_normalize_title(title),
            description=_normalize_optional_text(description),
            visibility=_normalize_visibility(visibility),
        )
        if updated is None:
            raise ValidationError("Playlist is not found.")
        return updated

    async def delete_playlist(self, actor_user_id: UUID, *, playlist_id: UUID) -> None:
        await self._require_owned_playlist(actor_user_id, playlist_id)
        if not await self._repository.delete_playlist(playlist_id):
            raise ValidationError("Playlist is not found.")

    async def get_my_playlist(self, actor_user_id: UUID, *, playlist_id: UUID) -> PlaylistReadModel:
        return await self._require_owned_playlist(actor_user_id, playlist_id)

    async def list_my_playlists(self, actor_user_id: UUID, *, limit: int, offset: int) -> list[PlaylistReadModel]:
        paging_limit, paging_offset = _normalize_paging(limit, offset)
        return await self._repository.list_playlists(
            PlaylistListFilter(
                owner_user_id=actor_user_id,
                limit=paging_limit,
                offset=paging_offset,
            )
        )

    async def list_public_playlists(self, *, limit: int, offset: int) -> list[PlaylistReadModel]:
        paging_limit, paging_offset = _normalize_paging(limit, offset)
        return await self._repository.list_playlists(
            PlaylistListFilter(
                visibility="public",
                limit=paging_limit,
                offset=paging_offset,
            )
        )

    async def get_public_playlist(self, playlist_id: UUID) -> PlaylistReadModel:
        playlist = await self._repository.get_playlist_by_id(playlist_id)
        if playlist is None:
            raise ValidationError("Playlist is not found.")
        if playlist.visibility == "private":
            raise ValidationError("Playlist is private.")
        return playlist

    async def add_track(
        self,
        actor_user_id: UUID,
        *,
        playlist_id: UUID,
        track_id: UUID,
        position: int | None,
    ) -> PlaylistReadModel:
        playlist = await self._require_owned_playlist(actor_user_id, playlist_id)
        if not await self._repository.track_exists(track_id):
            raise ValidationError("Track is not found.")
        existing_ids = {item.track_id for item in playlist.track_items}
        if track_id in existing_ids:
            raise ValidationError("Track is already in playlist.")
        next_tracks = list(playlist.track_items)
        insert_position = _normalize_insert_position(position, len(next_tracks))
        next_tracks.insert(
            insert_position - 1,
            PlaylistTrackItemReadModel(
                track_id=track_id,
                added_by_user_id=actor_user_id,
                position=insert_position,
                added_at=datetime.now(UTC),
            ),
        )
        normalized_tracks = _renumber_tracks(next_tracks)
        await self._repository.replace_playlist_tracks(playlist_id, normalized_tracks)
        refreshed = await self._repository.get_playlist_by_id(playlist_id)
        if refreshed is None:
            raise ValidationError("Playlist is not found.")
        return refreshed

    async def remove_track(self, actor_user_id: UUID, *, playlist_id: UUID, track_id: UUID) -> PlaylistReadModel:
        playlist = await self._require_owned_playlist(actor_user_id, playlist_id)
        if track_id not in {item.track_id for item in playlist.track_items}:
            raise ValidationError("Track is not found in playlist.")
        remaining_tracks = [item for item in playlist.track_items if item.track_id != track_id]
        await self._repository.replace_playlist_tracks(playlist_id, _renumber_tracks(remaining_tracks))
        refreshed = await self._repository.get_playlist_by_id(playlist_id)
        if refreshed is None:
            raise ValidationError("Playlist is not found.")
        return refreshed

    async def reorder_tracks(self, actor_user_id: UUID, *, playlist_id: UUID, track_ids: list[UUID]) -> PlaylistReadModel:
        playlist = await self._require_owned_playlist(actor_user_id, playlist_id)
        if not track_ids:
            raise ValidationError("Track order should not be empty.")
        unique_track_ids = list(dict.fromkeys(track_ids))
        if len(unique_track_ids) != len(track_ids):
            raise ValidationError("Track ids should not contain duplicates.")
        current_track_ids = [item.track_id for item in playlist.track_items]
        if set(unique_track_ids) != set(current_track_ids) or len(unique_track_ids) != len(current_track_ids):
            raise ValidationError("Track order should contain exactly current playlist tracks.")
        by_track_id = {item.track_id: item for item in playlist.track_items}
        reordered = [
            PlaylistTrackItemReadModel(
                track_id=track_id,
                added_by_user_id=by_track_id[track_id].added_by_user_id,
                position=index + 1,
                added_at=by_track_id[track_id].added_at,
            )
            for index, track_id in enumerate(unique_track_ids)
        ]
        await self._repository.replace_playlist_tracks(playlist_id, reordered)
        refreshed = await self._repository.get_playlist_by_id(playlist_id)
        if refreshed is None:
            raise ValidationError("Playlist is not found.")
        return refreshed

    async def _require_owned_playlist(self, actor_user_id: UUID, playlist_id: UUID) -> PlaylistReadModel:
        playlist = await self._repository.get_playlist_by_id(playlist_id)
        if playlist is None:
            raise ValidationError("Playlist is not found.")
        if playlist.owner_user_id != actor_user_id:
            raise AuthorizationError("Playlist is not owned by current user.")
        return playlist


def _normalize_title(value: str) -> str:
    normalized = value.strip()
    if len(normalized) < 1 or len(normalized) > 255:
        raise ValidationError("Title length should be between 1 and 255 characters.")
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 4000:
        raise ValidationError("Description should contain at most 4000 characters.")
    return normalized


def _normalize_visibility(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in PLAYLIST_VISIBILITIES:
        raise ValidationError("Unsupported playlist visibility.")
    return normalized


def _normalize_paging(limit: int, offset: int) -> tuple[int, int]:
    if limit < 1 or limit > 100:
        raise ValidationError("Limit should be between 1 and 100.")
    if offset < 0:
        raise ValidationError("Offset should be a non-negative number.")
    return limit, offset


def _normalize_insert_position(position: int | None, current_size: int) -> int:
    if position is None:
        return current_size + 1
    if position < 1 or position > current_size + 1:
        raise ValidationError("Track position is out of allowed playlist range.")
    return position


def _renumber_tracks(items: list[PlaylistTrackItemReadModel]) -> list[PlaylistTrackItemReadModel]:
    return [
        PlaylistTrackItemReadModel(
            track_id=item.track_id,
            added_by_user_id=item.added_by_user_id,
            position=index + 1,
            added_at=item.added_at,
        )
        for index, item in enumerate(items)
    ]
