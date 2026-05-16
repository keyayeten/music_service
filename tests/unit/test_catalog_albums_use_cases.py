from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from backend.application.catalog.use_cases.albums import CatalogAlbumUseCases
from backend.domain.catalog.repositories import AlbumReadModel, AlbumTrackReadModel
from backend.domain.common.exceptions import AuthorizationError, ValidationError


class _FakeCatalogRepository:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.composer_profile_id = uuid4()
        self.album_id = uuid4()
        self.album = AlbumReadModel(
            id=self.album_id,
            owner_composer_id=self.composer_profile_id,
            title="Album",
            description=None,
            status="draft",
            release_date=None,
            likes_count=0,
            comments_count=0,
            created_at=datetime.now(UTC),
            track_items=[],
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

    def create_album(self, *, owner_composer_id: UUID, title: str, description: str | None, release_date):
        self.album = AlbumReadModel(
            id=uuid4(),
            owner_composer_id=owner_composer_id,
            title=title,
            description=description,
            status="draft",
            release_date=release_date,
            likes_count=0,
            comments_count=0,
            created_at=datetime.now(UTC),
            track_items=[],
        )
        return self.album

    def update_album(self, *, album_id: UUID, title: str, description: str | None, release_date):
        if self.album.id != album_id:
            return None
        self.album = AlbumReadModel(
            id=self.album.id,
            owner_composer_id=self.album.owner_composer_id,
            title=title,
            description=description,
            status=self.album.status,
            release_date=release_date,
            likes_count=self.album.likes_count,
            comments_count=self.album.comments_count,
            created_at=self.album.created_at,
            track_items=self.album.track_items,
        )
        return self.album

    def replace_album_tracks(self, album_id: UUID, track_ids: list[UUID]) -> None:
        if self.album.id != album_id:
            return
        track_items = [AlbumTrackReadModel(track_id=track_id, position=index + 1) for index, track_id in enumerate(track_ids)]
        self.album = AlbumReadModel(
            id=self.album.id,
            owner_composer_id=self.album.owner_composer_id,
            title=self.album.title,
            description=self.album.description,
            status=self.album.status,
            release_date=self.album.release_date,
            likes_count=self.album.likes_count,
            comments_count=self.album.comments_count,
            created_at=self.album.created_at,
            track_items=track_items,
        )

    def set_album_status(self, album_id: UUID, status: str):
        if self.album.id != album_id:
            return None
        self.album = AlbumReadModel(
            id=self.album.id,
            owner_composer_id=self.album.owner_composer_id,
            title=self.album.title,
            description=self.album.description,
            status=status,
            release_date=self.album.release_date,
            likes_count=self.album.likes_count,
            comments_count=self.album.comments_count,
            created_at=self.album.created_at,
            track_items=self.album.track_items,
        )
        return self.album

    def get_album_by_id(self, album_id: UUID):
        if self.album.id == album_id:
            return self.album
        return None

    def list_albums(self, _filters):
        return [self.album]


@pytest.mark.unit
def test_replace_album_tracks_deduplicates_track_ids() -> None:
    repository = _FakeCatalogRepository()
    use_cases = CatalogAlbumUseCases(repository=repository)
    track_id = uuid4()

    result = use_cases.replace_album_tracks(repository.user_id, album_id=repository.album_id, track_ids=[track_id, track_id])

    assert len(result.track_items) == 1
    assert result.track_items[0].track_id == track_id
    assert result.track_items[0].position == 1


@pytest.mark.unit
def test_publish_album_requires_valid_transition() -> None:
    repository = _FakeCatalogRepository()
    repository.album = repository.set_album_status(repository.album_id, "pending_review")
    use_cases = CatalogAlbumUseCases(repository=repository)

    with pytest.raises(ValidationError):
        use_cases.publish_album(repository.user_id, album_id=repository.album_id)


@pytest.mark.unit
def test_moderate_album_requires_privileged_role() -> None:
    repository = _FakeCatalogRepository()
    repository.album = repository.set_album_status(repository.album_id, "pending_review")
    use_cases = CatalogAlbumUseCases(repository=repository)

    with pytest.raises(AuthorizationError):
        use_cases.moderate_album(["user"], album_id=repository.album_id, target_status="published")


@pytest.mark.unit
def test_create_album_requires_composer_role() -> None:
    repository = _FakeCatalogRepository()
    repository.role_codes = {"user"}
    use_cases = CatalogAlbumUseCases(repository=repository)

    with pytest.raises(AuthorizationError):
        use_cases.create_album(repository.user_id, title="Album", description=None, release_date=None)
