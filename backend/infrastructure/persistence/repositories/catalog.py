from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.catalog.repositories import (
    AlbumListFilter,
    AlbumReadModel,
    AlbumTrackReadModel,
    CatalogRepository,
    TrackAuthorReadModel,
    TrackListFilter,
    TrackReadModel,
)
from backend.infrastructure.persistence.models.catalog import (
    Album,
    AlbumTrack,
    Genre,
    Track,
    TrackAuthor,
    TrackGenre,
)
from backend.infrastructure.persistence.models.identity import ComposerProfile, Role, UserRole


class SqlAlchemyCatalogRepository(CatalogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_role_codes(self, user_id: UUID) -> list[str]:
        query = (
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.code.asc())
        )
        return list((await self._session.execute(query)).scalars())

    async def get_composer_profile_id_by_user_id(self, user_id: UUID) -> UUID | None:
        return (
            await self._session.execute(
                select(ComposerProfile.id).where(ComposerProfile.user_id == user_id)
            )
        ).scalar_one_or_none()

    async def create_track(
        self,
        *,
        title: str,
        description: str | None,
        duration_seconds: int,
        primary_author_id: UUID,
    ) -> TrackReadModel:
        track = Track(
            title=title,
            description=description,
            duration_seconds=duration_seconds,
            status="draft",
        )
        self._session.add(track)
        await self._session.flush()
        self._session.add(
            TrackAuthor(
                track_id=track.id,
                composer_profile_id=primary_author_id,
                contribution_role="composer",
                position=1,
            )
        )
        await self._session.flush()
        created_track = await self.get_track_by_id(track.id)
        assert created_track is not None
        return created_track

    async def update_track(
        self,
        *,
        track_id: UUID,
        title: str,
        description: str | None,
        duration_seconds: int,
    ) -> TrackReadModel | None:
        track = await self._session.get(Track, track_id)
        if track is None:
            return None
        track.title = title
        track.description = description
        track.duration_seconds = duration_seconds
        await self._session.flush()
        return await self.get_track_by_id(track_id)

    async def replace_track_authors(
        self, track_id: UUID, authors: list[TrackAuthorReadModel]
    ) -> None:
        await self._session.execute(delete(TrackAuthor).where(TrackAuthor.track_id == track_id))
        for author in authors:
            self._session.add(
                TrackAuthor(
                    track_id=track_id,
                    composer_profile_id=author.composer_profile_id,
                    contribution_role=author.contribution_role,
                    position=author.position,
                )
            )
        await self._session.flush()

    async def set_track_status(
        self, track_id: UUID, status: str, published_at: datetime | None
    ) -> TrackReadModel | None:
        track = await self._session.get(Track, track_id)
        if track is None:
            return None
        track.status = status
        track.published_at = published_at
        await self._session.flush()
        return await self.get_track_by_id(track_id)

    async def get_track_by_id(self, track_id: UUID) -> TrackReadModel | None:
        track = await self._session.get(Track, track_id)
        if track is None:
            return None
        author_map = await self._load_track_authors([track.id])
        genre_map = await self._load_track_genres([track.id])
        return _to_track_read_model(track, author_map[track.id], genre_map[track.id])

    async def list_tracks(self, filters: TrackListFilter) -> list[TrackReadModel]:
        query = select(Track).order_by(desc(Track.published_at), desc(Track.created_at))
        if filters.status is not None:
            query = query.where(Track.status == filters.status)
        if not filters.include_unpublished:
            query = query.where(Track.status == "published")
        if filters.author_id is not None:
            query = query.join(TrackAuthor, TrackAuthor.track_id == Track.id).where(
                TrackAuthor.composer_profile_id == filters.author_id
            )
        if filters.genre_code is not None:
            query = (
                query.join(TrackGenre, TrackGenre.track_id == Track.id)
                .join(Genre, Genre.id == TrackGenre.genre_id)
                .where(Genre.code == filters.genre_code)
            )
        tracks = list((await self._session.execute(query.distinct())).scalars())
        if not tracks:
            return []
        track_ids = [item.id for item in tracks]
        author_map = await self._load_track_authors(track_ids)
        genre_map = await self._load_track_genres(track_ids)
        return [
            _to_track_read_model(item, author_map[item.id], genre_map[item.id]) for item in tracks
        ]

    async def create_album(
        self,
        *,
        owner_composer_id: UUID,
        title: str,
        description: str | None,
        release_date: date | None,
    ) -> AlbumReadModel:
        album = Album(
            owner_composer_id=owner_composer_id,
            title=title,
            description=description,
            status="draft",
            release_date=release_date,
        )
        self._session.add(album)
        await self._session.flush()
        created_album = await self.get_album_by_id(album.id)
        assert created_album is not None
        return created_album

    async def update_album(
        self,
        *,
        album_id: UUID,
        title: str,
        description: str | None,
        release_date: date | None,
    ) -> AlbumReadModel | None:
        album = await self._session.get(Album, album_id)
        if album is None:
            return None
        album.title = title
        album.description = description
        album.release_date = release_date
        await self._session.flush()
        return await self.get_album_by_id(album_id)

    async def replace_album_tracks(self, album_id: UUID, track_ids: list[UUID]) -> None:
        await self._session.execute(delete(AlbumTrack).where(AlbumTrack.album_id == album_id))
        for index, track_id in enumerate(track_ids):
            self._session.add(
                AlbumTrack(
                    album_id=album_id,
                    track_id=track_id,
                    position=index + 1,
                )
            )
        await self._session.flush()

    async def set_album_status(self, album_id: UUID, status: str) -> AlbumReadModel | None:
        album = await self._session.get(Album, album_id)
        if album is None:
            return None
        album.status = status
        await self._session.flush()
        return await self.get_album_by_id(album_id)

    async def get_album_by_id(self, album_id: UUID) -> AlbumReadModel | None:
        album = await self._session.get(Album, album_id)
        if album is None:
            return None
        tracks_map = await self._load_album_tracks([album.id])
        return _to_album_read_model(album, tracks_map[album.id])

    async def list_albums(self, filters: AlbumListFilter) -> list[AlbumReadModel]:
        query = select(Album).order_by(desc(Album.release_date), desc(Album.created_at))
        if filters.status is not None:
            query = query.where(Album.status == filters.status)
        if filters.owner_composer_id is not None:
            query = query.where(Album.owner_composer_id == filters.owner_composer_id)
        if not filters.include_unpublished:
            query = query.where(Album.status == "published")
        albums = list((await self._session.execute(query)).scalars())
        if not albums:
            return []
        album_ids = [item.id for item in albums]
        tracks_map = await self._load_album_tracks(album_ids)
        return [_to_album_read_model(item, tracks_map[item.id]) for item in albums]

    async def _load_track_authors(
        self, track_ids: list[UUID]
    ) -> dict[UUID, list[TrackAuthorReadModel]]:
        rows = (
            await self._session.execute(
                select(TrackAuthor)
                .where(TrackAuthor.track_id.in_(track_ids))
                .order_by(TrackAuthor.position.asc())
            )
        ).scalars()
        author_map: dict[UUID, list[TrackAuthorReadModel]] = defaultdict(list)
        for row in rows:
            author_map[row.track_id].append(
                TrackAuthorReadModel(
                    composer_profile_id=row.composer_profile_id,
                    contribution_role=row.contribution_role,
                    position=row.position,
                )
            )
        return author_map

    async def _load_track_genres(self, track_ids: list[UUID]) -> dict[UUID, list[str]]:
        rows = (
            await self._session.execute(
                select(TrackGenre.track_id, Genre.code)
                .join(Genre, Genre.id == TrackGenre.genre_id)
                .where(TrackGenre.track_id.in_(track_ids))
                .order_by(Genre.code.asc())
            )
        ).all()
        genre_map: dict[UUID, list[str]] = defaultdict(list)
        for track_id, genre_code in rows:
            genre_map[track_id].append(genre_code)
        return genre_map

    async def _load_album_tracks(
        self, album_ids: list[UUID]
    ) -> dict[UUID, list[AlbumTrackReadModel]]:
        rows = (
            await self._session.execute(
                select(AlbumTrack)
                .where(AlbumTrack.album_id.in_(album_ids))
                .order_by(AlbumTrack.album_id.asc(), AlbumTrack.position.asc())
            )
        ).scalars()
        track_map: dict[UUID, list[AlbumTrackReadModel]] = defaultdict(list)
        for row in rows:
            track_map[row.album_id].append(
                AlbumTrackReadModel(
                    track_id=row.track_id,
                    position=row.position,
                )
            )
        return track_map


def _to_track_read_model(
    track: Track, authors: list[TrackAuthorReadModel], genre_codes: list[str]
) -> TrackReadModel:
    return TrackReadModel(
        id=track.id,
        title=track.title,
        description=track.description,
        status=track.status,
        duration_seconds=track.duration_seconds,
        plays_count=track.plays_count,
        likes_count=track.likes_count,
        comments_count=track.comments_count,
        published_at=track.published_at,
        created_at=track.created_at,
        authors=authors,
        genre_codes=genre_codes,
    )


def _to_album_read_model(album: Album, track_items: list[AlbumTrackReadModel]) -> AlbumReadModel:
    return AlbumReadModel(
        id=album.id,
        owner_composer_id=album.owner_composer_id,
        title=album.title,
        description=album.description,
        status=album.status,
        release_date=album.release_date,
        likes_count=album.likes_count,
        comments_count=album.comments_count,
        created_at=album.created_at,
        track_items=track_items,
    )
