from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.library.repositories import (
    LibraryItemReadModel,
    LibraryListFilter,
    LibraryRepository,
    PlaylistListFilter,
    PlaylistReadModel,
    PlaylistTrackItemReadModel,
)
from backend.infrastructure.persistence.models.catalog import Album, Track
from backend.infrastructure.persistence.models.library import LibraryItem, Playlist, PlaylistTrack


class SqlAlchemyLibraryRepository(LibraryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_playlist(
        self,
        *,
        owner_user_id: UUID,
        title: str,
        description: str | None,
        visibility: str,
    ) -> PlaylistReadModel:
        playlist = Playlist(
            owner_user_id=owner_user_id,
            title=title,
            description=description,
            visibility=visibility,
        )
        self._session.add(playlist)
        await self._session.flush()
        created = await self.get_playlist_by_id(playlist.id)
        assert created is not None
        return created

    async def update_playlist(
        self,
        *,
        playlist_id: UUID,
        title: str,
        description: str | None,
        visibility: str,
    ) -> PlaylistReadModel | None:
        playlist = await self._session.get(Playlist, playlist_id)
        if playlist is None:
            return None
        playlist.title = title
        playlist.description = description
        playlist.visibility = visibility
        await self._session.flush()
        return await self.get_playlist_by_id(playlist_id)

    async def delete_playlist(self, playlist_id: UUID) -> bool:
        playlist = await self._session.get(Playlist, playlist_id)
        if playlist is None:
            return False
        await self._session.delete(playlist)
        await self._session.flush()
        return True

    async def get_playlist_by_id(self, playlist_id: UUID) -> PlaylistReadModel | None:
        playlist = await self._session.get(Playlist, playlist_id)
        if playlist is None:
            return None
        tracks_map = await self._load_playlist_tracks([playlist.id])
        return _to_playlist_read_model(playlist, tracks_map[playlist.id])

    async def list_playlists(self, filters: PlaylistListFilter) -> list[PlaylistReadModel]:
        query = select(Playlist).order_by(desc(Playlist.created_at))
        if filters.owner_user_id is not None:
            query = query.where(Playlist.owner_user_id == filters.owner_user_id)
        if filters.visibility is not None:
            query = query.where(Playlist.visibility == filters.visibility)
        if filters.include_unlisted:
            query = query.where(Playlist.visibility.in_(("public", "unlisted")))
        query = query.limit(filters.limit).offset(filters.offset)
        playlists = list((await self._session.execute(query)).scalars())
        if not playlists:
            return []
        playlist_ids = [item.id for item in playlists]
        track_map = await self._load_playlist_tracks(playlist_ids)
        return [_to_playlist_read_model(item, track_map[item.id]) for item in playlists]

    async def add_playlist_track(
        self,
        *,
        playlist_id: UUID,
        track_id: UUID,
        added_by_user_id: UUID,
        position: int,
    ) -> None:
        self._session.add(
            PlaylistTrack(
                playlist_id=playlist_id,
                track_id=track_id,
                added_by_user_id=added_by_user_id,
                position=position,
            )
        )
        await self._session.flush()

    async def remove_playlist_track(self, *, playlist_id: UUID, track_id: UUID) -> bool:
        result = await self._session.execute(
            delete(PlaylistTrack).where(
                PlaylistTrack.playlist_id == playlist_id,
                PlaylistTrack.track_id == track_id,
            )
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def replace_playlist_tracks(self, playlist_id: UUID, tracks: list[PlaylistTrackItemReadModel]) -> None:
        await self._session.execute(delete(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id))
        for item in tracks:
            self._session.add(
                PlaylistTrack(
                    playlist_id=playlist_id,
                    track_id=item.track_id,
                    added_by_user_id=item.added_by_user_id,
                    position=item.position,
                    added_at=item.added_at,
                )
            )
        await self._session.flush()

    async def get_playlist_track_count(self, playlist_id: UUID) -> int:
        return (
            (await self._session.execute(
                select(func.count()).select_from(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id)
            )).scalar_one()
            or 0
        )

    async def track_exists(self, track_id: UUID) -> bool:
        return await self._session.get(Track, track_id) is not None

    async def add_library_item(
        self,
        *,
        user_id: UUID,
        item_type: str,
        item_id: UUID,
        section: str,
    ) -> LibraryItemReadModel:
        item = LibraryItem(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            section=section,
        )
        self._session.add(item)
        await self._session.flush()
        return _to_library_item_read_model(item)

    async def remove_library_item(self, *, user_id: UUID, item_type: str, item_id: UUID) -> bool:
        result = await self._session.execute(
            delete(LibraryItem).where(
                LibraryItem.user_id == user_id,
                LibraryItem.item_type == item_type,
                LibraryItem.item_id == item_id,
            )
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def list_library_items(self, filters: LibraryListFilter) -> list[LibraryItemReadModel]:
        query = (
            select(LibraryItem)
            .where(LibraryItem.user_id == filters.user_id)
            .order_by(desc(LibraryItem.created_at))
            .limit(filters.limit)
            .offset(filters.offset)
        )
        if filters.section is not None:
            query = query.where(LibraryItem.section == filters.section)
        if filters.item_type is not None:
            query = query.where(LibraryItem.item_type == filters.item_type)
        items = list((await self._session.execute(query)).scalars())
        return [_to_library_item_read_model(item) for item in items]

    async def item_exists(self, item_type: str, item_id: UUID) -> bool:
        if item_type == "track":
            return await self._session.get(Track, item_id) is not None
        if item_type == "album":
            return await self._session.get(Album, item_id) is not None
        if item_type == "playlist":
            return await self._session.get(Playlist, item_id) is not None
        return False

    async def _load_playlist_tracks(self, playlist_ids: list[UUID]) -> dict[UUID, list[PlaylistTrackItemReadModel]]:
        rows = (await self._session.execute(
            select(PlaylistTrack)
            .where(PlaylistTrack.playlist_id.in_(playlist_ids))
            .order_by(PlaylistTrack.playlist_id.asc(), PlaylistTrack.position.asc())
        )).scalars()
        track_map: dict[UUID, list[PlaylistTrackItemReadModel]] = defaultdict(list)
        for row in rows:
            track_map[row.playlist_id].append(
                PlaylistTrackItemReadModel(
                    track_id=row.track_id,
                    added_by_user_id=row.added_by_user_id,
                    position=row.position,
                    added_at=row.added_at,
                )
            )
        return track_map


def _to_playlist_read_model(playlist: Playlist, track_items: list[PlaylistTrackItemReadModel]) -> PlaylistReadModel:
    return PlaylistReadModel(
        id=playlist.id,
        owner_user_id=playlist.owner_user_id,
        title=playlist.title,
        description=playlist.description,
        visibility=playlist.visibility,
        likes_count=playlist.likes_count,
        comments_count=playlist.comments_count,
        created_at=playlist.created_at,
        track_items=track_items,
    )


def _to_library_item_read_model(item: LibraryItem) -> LibraryItemReadModel:
    return LibraryItemReadModel(
        id=item.id,
        user_id=item.user_id,
        item_type=item.item_type,
        item_id=item.item_id,
        section=item.section,
        created_at=item.created_at,
    )
