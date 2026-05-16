from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from backend.application.library.use_cases.playlists import LibraryPlaylistUseCases
from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.domain.library.repositories import PlaylistReadModel, PlaylistTrackItemReadModel
from tests.async_tools import run_async


class _FakeLibraryRepository:
    def __init__(self) -> None:
        self.owner_id = uuid4()
        self.other_user_id = uuid4()
        self.track_a = uuid4()
        self.track_b = uuid4()
        self.playlist_id = uuid4()
        self._playlists: dict[UUID, PlaylistReadModel] = {
            self.playlist_id: PlaylistReadModel(
                id=self.playlist_id,
                owner_user_id=self.owner_id,
                title="Stage4 Playlist",
                description=None,
                visibility="public",
                likes_count=0,
                comments_count=0,
                created_at=datetime.now(UTC),
                track_items=[
                    PlaylistTrackItemReadModel(
                        track_id=self.track_a,
                        added_by_user_id=self.owner_id,
                        position=1,
                        added_at=datetime.now(UTC),
                    ),
                    PlaylistTrackItemReadModel(
                        track_id=self.track_b,
                        added_by_user_id=self.owner_id,
                        position=2,
                        added_at=datetime.now(UTC),
                    ),
                ],
            )
        }

    async def create_playlist(self, **kwargs):
        raise NotImplementedError

    async def update_playlist(self, **kwargs):
        raise NotImplementedError

    async def delete_playlist(self, playlist_id: UUID) -> bool:
        return bool(self._playlists.pop(playlist_id, None))

    async def get_playlist_by_id(self, playlist_id: UUID) -> PlaylistReadModel | None:
        return self._playlists.get(playlist_id)

    async def list_playlists(self, _filters):
        return list(self._playlists.values())

    async def add_playlist_track(self, **kwargs):
        raise NotImplementedError

    async def remove_playlist_track(self, *, playlist_id: UUID, track_id: UUID) -> bool:
        playlist = self._playlists.get(playlist_id)
        if playlist is None:
            return False
        if track_id not in {item.track_id for item in playlist.track_items}:
            return False
        self._playlists[playlist_id] = PlaylistReadModel(
            id=playlist.id,
            owner_user_id=playlist.owner_user_id,
            title=playlist.title,
            description=playlist.description,
            visibility=playlist.visibility,
            likes_count=playlist.likes_count,
            comments_count=playlist.comments_count,
            created_at=playlist.created_at,
            track_items=[item for item in playlist.track_items if item.track_id != track_id],
        )
        return True

    async def replace_playlist_tracks(self, playlist_id: UUID, tracks: list[PlaylistTrackItemReadModel]) -> None:
        playlist = self._playlists[playlist_id]
        self._playlists[playlist_id] = PlaylistReadModel(
            id=playlist.id,
            owner_user_id=playlist.owner_user_id,
            title=playlist.title,
            description=playlist.description,
            visibility=playlist.visibility,
            likes_count=playlist.likes_count,
            comments_count=playlist.comments_count,
            created_at=playlist.created_at,
            track_items=tracks,
        )

    async def get_playlist_track_count(self, playlist_id: UUID) -> int:
        return len(self._playlists[playlist_id].track_items)

    async def track_exists(self, track_id: UUID) -> bool:
        return track_id in {self.track_a, self.track_b}

    async def add_library_item(self, **kwargs):
        raise NotImplementedError

    async def remove_library_item(self, **kwargs):
        raise NotImplementedError

    async def list_library_items(self, **kwargs):
        raise NotImplementedError

    async def item_exists(self, **kwargs):
        raise NotImplementedError


@pytest.mark.unit
def test_reorder_playlist_tracks_applies_new_positions() -> None:
    repository = _FakeLibraryRepository()
    use_cases = LibraryPlaylistUseCases(repository=repository)

    result = run_async(
        use_cases.reorder_tracks(
            repository.owner_id,
            playlist_id=repository.playlist_id,
            track_ids=[repository.track_b, repository.track_a],
        )
    )

    assert [item.track_id for item in result.track_items] == [repository.track_b, repository.track_a]
    assert [item.position for item in result.track_items] == [1, 2]


@pytest.mark.unit
def test_reorder_playlist_tracks_requires_same_track_set() -> None:
    repository = _FakeLibraryRepository()
    use_cases = LibraryPlaylistUseCases(repository=repository)

    with pytest.raises(ValidationError):
        run_async(
            use_cases.reorder_tracks(
                repository.owner_id,
                playlist_id=repository.playlist_id,
                track_ids=[repository.track_a],
            )
        )


@pytest.mark.unit
def test_update_playlist_requires_owner() -> None:
    repository = _FakeLibraryRepository()
    use_cases = LibraryPlaylistUseCases(repository=repository)

    with pytest.raises(AuthorizationError):
        run_async(
            use_cases.update_playlist(
                repository.other_user_id,
                playlist_id=repository.playlist_id,
                title="New title",
                description="New description",
                visibility="public",
            )
        )
