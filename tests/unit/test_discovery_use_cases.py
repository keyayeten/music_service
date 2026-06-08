from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from backend.application.discovery.use_cases.events_and_recommendations import DiscoveryUseCases
from backend.domain.common.exceptions import ValidationError
from backend.domain.discovery.repositories import RecommendedTrackReadModel, UserTrackEventReadModel
from tests.async_tools import run_async


class _FakeDiscoveryRepository:
    def __init__(self) -> None:
        self.track_a = uuid4()
        self.track_b = uuid4()
        self.events: list[UserTrackEventReadModel] = []

    async def record_user_track_event(
        self,
        *,
        user_id: UUID,
        track_id: UUID,
        event_type: str,
        metadata: dict | None = None,
    ) -> UserTrackEventReadModel:
        created = UserTrackEventReadModel(
            id=uuid4(),
            user_id=user_id,
            track_id=track_id,
            event_type=event_type,
            created_at=datetime.now(UTC),
        )
        self.events.append(created)
        return created

    async def record_external_link_click(
        self,
        *,
        user_id: UUID,
        external_link_id: UUID,
        track_id: UUID,
        metadata: dict | None = None,
    ) -> None:
        return None

    async def get_track_ids_for_item(self, *, item_type: str, item_id: UUID) -> list[UUID]:
        if item_type == "track":
            return [self.track_a]
        if item_type == "album":
            return [self.track_a, self.track_b]
        return []

    async def get_track_ids_for_target(self, *, target_type: str, target_id: UUID) -> list[UUID]:
        return await self.get_track_ids_for_item(item_type=target_type, item_id=target_id)

    async def get_track_id_by_external_link_id(self, external_link_id: UUID) -> UUID | None:
        return self.track_a

    async def increment_track_plays_count(self, track_id: UUID) -> None:
        return None

    async def get_user_recommended_tracks(
        self, *, user_id: UUID, limit: int
    ) -> list[RecommendedTrackReadModel]:
        return [RecommendedTrackReadModel(track_id=self.track_b, score=9.0, source="personalized")]

    async def get_top_published_tracks(self, *, limit: int) -> list[RecommendedTrackReadModel]:
        return [RecommendedTrackReadModel(track_id=self.track_a, score=3.0, source="top_published")]


@pytest.mark.unit
def test_record_save_events_for_album_produces_event_per_track() -> None:
    repository = _FakeDiscoveryRepository()
    use_cases = DiscoveryUseCases(repository=repository)
    actor_user_id = uuid4()

    run_async(use_cases.record_save_events(actor_user_id, item_type="album", item_id=uuid4()))

    assert len(repository.events) == 2
    assert {item.track_id for item in repository.events} == {repository.track_a, repository.track_b}
    assert {item.event_type for item in repository.events} == {"save"}


@pytest.mark.unit
def test_record_view_events_rejects_empty_track_collection() -> None:
    repository = _FakeDiscoveryRepository()
    use_cases = DiscoveryUseCases(repository=repository)

    with pytest.raises(ValidationError):
        run_async(use_cases.record_view_events(uuid4(), track_ids=[]))


@pytest.mark.unit
def test_recommendations_use_personalized_or_top_fallback() -> None:
    repository = _FakeDiscoveryRepository()
    use_cases = DiscoveryUseCases(repository=repository)

    personalized = run_async(use_cases.list_recommended_tracks(actor_user_id=uuid4(), limit=20))
    fallback = run_async(use_cases.list_recommended_tracks(actor_user_id=None, limit=20))

    assert personalized[0].source == "personalized"
    assert fallback[0].source == "top_published"
