from __future__ import annotations

from uuid import UUID

from backend.domain.common.exceptions import ValidationError
from backend.domain.discovery.repositories import (
    TRACK_EVENT_TYPES,
    DiscoveryRepository,
    RecommendedTrackReadModel,
)


class DiscoveryUseCases:
    def __init__(self, repository: DiscoveryRepository) -> None:
        self._repository = repository

    def record_view_events(self, actor_user_id: UUID, *, track_ids: list[UUID]) -> None:
        self._record_event_for_tracks(actor_user_id, "view", track_ids)

    def record_like_events(self, actor_user_id: UUID, *, target_type: str, target_id: UUID) -> None:
        track_ids = self._repository.get_track_ids_for_target(
            target_type=_normalize_target_type(target_type),
            target_id=target_id,
        )
        self._record_event_for_tracks(actor_user_id, "like", track_ids)

    def record_save_events(self, actor_user_id: UUID, *, item_type: str, item_id: UUID) -> None:
        track_ids = self._repository.get_track_ids_for_item(
            item_type=_normalize_item_type(item_type),
            item_id=item_id,
        )
        self._record_event_for_tracks(actor_user_id, "save", track_ids)

    def record_comment_events(self, actor_user_id: UUID, *, target_type: str, target_id: UUID) -> None:
        track_ids = self._repository.get_track_ids_for_target(
            target_type=_normalize_target_type(target_type),
            target_id=target_id,
        )
        self._record_event_for_tracks(actor_user_id, "comment", track_ids)

    def record_playlist_add_event(self, actor_user_id: UUID, *, track_id: UUID) -> None:
        self._record_event_for_tracks(actor_user_id, "playlist_add", [track_id])

    def record_external_click_event(self, actor_user_id: UUID, *, external_link_id: UUID) -> None:
        track_id = self._repository.get_track_id_by_external_link_id(external_link_id)
        if track_id is None:
            raise ValidationError("External link should reference a track.")
        self._repository.record_external_link_click(
            user_id=actor_user_id,
            external_link_id=external_link_id,
            track_id=track_id,
        )
        self._repository.increment_track_plays_count(track_id)
        self._repository.record_user_track_event(
            user_id=actor_user_id,
            track_id=track_id,
            event_type="external_click",
        )

    def list_recommended_tracks(
        self,
        *,
        actor_user_id: UUID | None,
        limit: int,
    ) -> list[RecommendedTrackReadModel]:
        normalized_limit = _normalize_limit(limit)
        if actor_user_id is None:
            return self._repository.get_top_published_tracks(limit=normalized_limit)
        personalized = self._repository.get_user_recommended_tracks(user_id=actor_user_id, limit=normalized_limit)
        if personalized:
            return personalized
        return self._repository.get_top_published_tracks(limit=normalized_limit)

    def _record_event_for_tracks(self, actor_user_id: UUID, event_type: str, track_ids: list[UUID]) -> None:
        normalized_event_type = _normalize_event_type(event_type)
        if not track_ids:
            raise ValidationError("Could not resolve tracks for event source.")
        for track_id in track_ids:
            self._repository.record_user_track_event(
                user_id=actor_user_id,
                track_id=track_id,
                event_type=normalized_event_type,
            )


def _normalize_event_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in TRACK_EVENT_TYPES:
        raise ValidationError("Unsupported track event type.")
    return normalized


def _normalize_item_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"track", "album", "playlist"}:
        raise ValidationError("Unsupported discovery item type.")
    return normalized


def _normalize_target_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"track", "album", "playlist"}:
        raise ValidationError("Unsupported discovery target type.")
    return normalized


def _normalize_limit(value: int) -> int:
    if value < 1 or value > 100:
        raise ValidationError("Limit should be between 1 and 100.")
    return value
