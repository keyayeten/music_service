from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from backend.application.catalog.use_cases.tracks import CatalogTrackUseCases
from backend.domain.catalog.repositories import TrackAuthorReadModel, TrackReadModel
from backend.domain.common.exceptions import AuthorizationError, ValidationError


class _FakeCatalogRepository:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.composer_profile_id = uuid4()
        self.track_id = uuid4()
        self.track = TrackReadModel(
            id=self.track_id,
            title="Initial",
            description=None,
            status="draft",
            duration_seconds=120,
            plays_count=0,
            likes_count=0,
            comments_count=0,
            published_at=None,
            created_at=datetime.now(UTC),
            authors=[
                TrackAuthorReadModel(
                    composer_profile_id=self.composer_profile_id,
                    contribution_role="composer",
                    position=1,
                )
            ],
            genre_codes=[],
        )
        self.role_codes = {"composer", "user"}

    def get_user_role_codes(self, user_id: UUID) -> list[str]:
        if user_id == self.user_id:
            return sorted(self.role_codes)
        return ["user"]

    def get_composer_profile_id_by_user_id(self, user_id: UUID) -> UUID | None:
        if user_id == self.user_id:
            return self.composer_profile_id
        return None

    def create_track(
        self,
        *,
        title: str,
        description: str | None,
        duration_seconds: int,
        primary_author_id: UUID,
    ) -> TrackReadModel:
        self.track = TrackReadModel(
            id=uuid4(),
            title=title,
            description=description,
            status="draft",
            duration_seconds=duration_seconds,
            plays_count=0,
            likes_count=0,
            comments_count=0,
            published_at=None,
            created_at=datetime.now(UTC),
            authors=[
                TrackAuthorReadModel(
                    composer_profile_id=primary_author_id,
                    contribution_role="composer",
                    position=1,
                )
            ],
            genre_codes=[],
        )
        return self.track

    def update_track(self, *, track_id: UUID, title: str, description: str | None, duration_seconds: int) -> TrackReadModel | None:
        if self.track.id != track_id:
            return None
        self.track = TrackReadModel(
            id=self.track.id,
            title=title,
            description=description,
            status=self.track.status,
            duration_seconds=duration_seconds,
            plays_count=self.track.plays_count,
            likes_count=self.track.likes_count,
            comments_count=self.track.comments_count,
            published_at=self.track.published_at,
            created_at=self.track.created_at,
            authors=self.track.authors,
            genre_codes=self.track.genre_codes,
        )
        return self.track

    def replace_track_authors(self, track_id: UUID, authors: list[TrackAuthorReadModel]) -> None:
        if self.track.id != track_id:
            return
        self.track = TrackReadModel(
            id=self.track.id,
            title=self.track.title,
            description=self.track.description,
            status=self.track.status,
            duration_seconds=self.track.duration_seconds,
            plays_count=self.track.plays_count,
            likes_count=self.track.likes_count,
            comments_count=self.track.comments_count,
            published_at=self.track.published_at,
            created_at=self.track.created_at,
            authors=authors,
            genre_codes=self.track.genre_codes,
        )

    def set_track_status(self, track_id: UUID, status: str, published_at: datetime | None) -> TrackReadModel | None:
        if self.track.id != track_id:
            return None
        self.track = TrackReadModel(
            id=self.track.id,
            title=self.track.title,
            description=self.track.description,
            status=status,
            duration_seconds=self.track.duration_seconds,
            plays_count=self.track.plays_count,
            likes_count=self.track.likes_count,
            comments_count=self.track.comments_count,
            published_at=published_at,
            created_at=self.track.created_at,
            authors=self.track.authors,
            genre_codes=self.track.genre_codes,
        )
        return self.track

    def get_track_by_id(self, track_id: UUID) -> TrackReadModel | None:
        if self.track.id == track_id:
            return self.track
        return None

    def list_tracks(self, _filters):
        return [self.track]


@pytest.mark.unit
def test_publish_track_sets_published_status() -> None:
    repository = _FakeCatalogRepository()
    use_cases = CatalogTrackUseCases(repository=repository)

    result = use_cases.publish_track(repository.user_id, track_id=repository.track_id)

    assert result.status == "published"
    assert result.published_at is not None


@pytest.mark.unit
def test_submit_review_rejects_invalid_transition() -> None:
    repository = _FakeCatalogRepository()
    repository.track = repository.set_track_status(repository.track_id, "published", datetime.now(UTC))
    use_cases = CatalogTrackUseCases(repository=repository)

    with pytest.raises(ValidationError):
        use_cases.submit_track_for_review(repository.user_id, track_id=repository.track_id)


@pytest.mark.unit
def test_moderation_requires_admin_or_moderator_role() -> None:
    repository = _FakeCatalogRepository()
    repository.track = repository.set_track_status(repository.track_id, "pending_review", None)
    use_cases = CatalogTrackUseCases(repository=repository)

    with pytest.raises(AuthorizationError):
        use_cases.moderate_track(["user"], track_id=repository.track_id, target_status="published")


@pytest.mark.unit
def test_set_track_authors_requires_current_composer_in_author_list() -> None:
    repository = _FakeCatalogRepository()
    use_cases = CatalogTrackUseCases(repository=repository)

    with pytest.raises(ValidationError):
        use_cases.set_track_authors(repository.user_id, track_id=repository.track_id, author_profile_ids=[uuid4()])


@pytest.mark.unit
def test_create_track_requires_composer_role() -> None:
    repository = _FakeCatalogRepository()
    repository.role_codes = {"user"}
    use_cases = CatalogTrackUseCases(repository=repository)

    with pytest.raises(AuthorizationError):
        use_cases.create_track(repository.user_id, title="Track", description=None, duration_seconds=120)
