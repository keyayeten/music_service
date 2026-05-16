from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

TRACK_EVENT_TYPES = {"view", "external_click", "like", "save", "comment", "playlist_add"}


@dataclass(frozen=True)
class UserTrackEventReadModel:
    id: UUID
    user_id: UUID
    track_id: UUID
    event_type: str
    created_at: datetime


@dataclass(frozen=True)
class RecommendedTrackReadModel:
    track_id: UUID
    score: float
    source: str


class DiscoveryRepository(Protocol):
    def record_user_track_event(
        self,
        *,
        user_id: UUID,
        track_id: UUID,
        event_type: str,
        metadata: dict | None = None,
    ) -> UserTrackEventReadModel:
        """Persist a user event for a concrete track."""

    def record_external_link_click(
        self,
        *,
        user_id: UUID,
        external_link_id: UUID,
        track_id: UUID,
        metadata: dict | None = None,
    ) -> None:
        """Persist detailed external link click event."""

    def get_track_ids_for_item(self, *, item_type: str, item_id: UUID) -> list[UUID]:
        """Map a polymorphic item to related track ids."""

    def get_track_ids_for_target(self, *, target_type: str, target_id: UUID) -> list[UUID]:
        """Map social target to related track ids."""

    def get_track_id_by_external_link_id(self, external_link_id: UUID) -> UUID | None:
        """Return track id for external link, if link belongs to track."""

    def increment_track_plays_count(self, track_id: UUID) -> None:
        """Increment denormalized plays counter for track."""

    def get_user_recommended_tracks(self, *, user_id: UUID, limit: int) -> list[RecommendedTrackReadModel]:
        """Return deterministic personalized track ranking for user."""

    def get_top_published_tracks(self, *, limit: int) -> list[RecommendedTrackReadModel]:
        """Return deterministic fallback ranking for published tracks."""
