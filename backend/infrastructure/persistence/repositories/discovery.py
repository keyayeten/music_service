from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.discovery.repositories import (
    DiscoveryRepository,
    RecommendedTrackReadModel,
    UserTrackEventReadModel,
)
from backend.infrastructure.persistence.models.catalog import AlbumTrack, ExternalLink, Track
from backend.infrastructure.persistence.models.discovery import ExternalLinkClick, UserTrackEvent
from backend.infrastructure.persistence.models.library import PlaylistTrack


class SqlAlchemyDiscoveryRepository(DiscoveryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_user_track_event(
        self,
        *,
        user_id: UUID,
        track_id: UUID,
        event_type: str,
        metadata: dict | None = None,
    ) -> UserTrackEventReadModel:
        entity = UserTrackEvent(
            user_id=user_id,
            track_id=track_id,
            event_type=event_type,
            event_metadata=metadata,
        )
        self._session.add(entity)
        await self._session.flush()
        return UserTrackEventReadModel(
            id=entity.id,
            user_id=entity.user_id,
            track_id=entity.track_id,
            event_type=entity.event_type,
            created_at=entity.created_at,
        )

    async def record_external_link_click(
        self,
        *,
        user_id: UUID,
        external_link_id: UUID,
        track_id: UUID,
        metadata: dict | None = None,
    ) -> None:
        self._session.add(
            ExternalLinkClick(
                user_id=user_id,
                external_link_id=external_link_id,
                track_id=track_id,
                click_metadata=metadata,
            )
        )
        await self._session.flush()

    async def get_track_ids_for_item(self, *, item_type: str, item_id: UUID) -> list[UUID]:
        if item_type == "track":
            track_id = (
                await self._session.execute(select(Track.id).where(Track.id == item_id).limit(1))
            ).scalar_one_or_none()
            return [track_id] if track_id else []
        if item_type == "album":
            rows = (
                await self._session.execute(
                    select(AlbumTrack.track_id)
                    .where(AlbumTrack.album_id == item_id)
                    .order_by(AlbumTrack.position.asc(), AlbumTrack.track_id.asc())
                )
            ).scalars()
            return list(rows)
        if item_type == "playlist":
            rows = (
                await self._session.execute(
                    select(PlaylistTrack.track_id)
                    .where(PlaylistTrack.playlist_id == item_id)
                    .order_by(PlaylistTrack.position.asc(), PlaylistTrack.track_id.asc())
                )
            ).scalars()
            return list(rows)
        return []

    async def get_track_ids_for_target(self, *, target_type: str, target_id: UUID) -> list[UUID]:
        return await self.get_track_ids_for_item(item_type=target_type, item_id=target_id)

    async def get_track_id_by_external_link_id(self, external_link_id: UUID) -> UUID | None:
        return (
            await self._session.execute(
                select(ExternalLink.entity_id)
                .where(ExternalLink.id == external_link_id, ExternalLink.entity_type == "track")
                .limit(1)
            )
        ).scalar_one_or_none()

    async def increment_track_plays_count(self, track_id: UUID) -> None:
        await self._session.execute(
            update(Track).where(Track.id == track_id).values(plays_count=Track.plays_count + 1)
        )
        await self._session.flush()

    async def get_user_recommended_tracks(
        self, *, user_id: UUID, limit: int
    ) -> list[RecommendedTrackReadModel]:
        score_expr = func.sum(
            case(
                (UserTrackEvent.event_type == "external_click", 6),
                (UserTrackEvent.event_type == "save", 5),
                (UserTrackEvent.event_type == "like", 4),
                (UserTrackEvent.event_type == "comment", 3),
                (UserTrackEvent.event_type == "playlist_add", 2),
                else_=1,
            )
        ).label("score")
        last_event_at = func.max(UserTrackEvent.created_at).label("last_event_at")
        rows = (
            await self._session.execute(
                select(UserTrackEvent.track_id, score_expr, last_event_at)
                .join(Track, Track.id == UserTrackEvent.track_id)
                .where(UserTrackEvent.user_id == user_id, Track.status == "published")
                .group_by(UserTrackEvent.track_id)
                .order_by(desc(score_expr), desc(last_event_at), UserTrackEvent.track_id.asc())
                .limit(limit)
            )
        ).all()
        return [
            RecommendedTrackReadModel(
                track_id=row.track_id,
                score=float(row.score),
                source="personalized",
            )
            for row in rows
        ]

    async def get_top_published_tracks(self, *, limit: int) -> list[RecommendedTrackReadModel]:
        score_expr = (
            Track.likes_count * 10 + Track.comments_count * 7 + Track.plays_count * 5
        ).label("score")
        rows = (
            await self._session.execute(
                select(Track.id, score_expr)
                .where(Track.status == "published")
                .order_by(
                    desc(score_expr),
                    desc(Track.published_at),
                    desc(Track.created_at),
                    Track.id.asc(),
                )
                .limit(limit)
            )
        ).all()
        return [
            RecommendedTrackReadModel(
                track_id=row.id,
                score=float(row.score),
                source="top_published",
            )
            for row in rows
        ]
