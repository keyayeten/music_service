from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import (
    get_api_response_cache,
    get_current_identity_user,
    get_db_session,
    get_discovery_use_cases,
    get_library_item_use_cases,
    get_library_playlist_use_cases,
)
from backend.api.v1.schemas.library import (
    AddLibraryItemRequest,
    AddPlaylistTrackRequest,
    CreatePlaylistRequest,
    LibraryItemResponse,
    ListLibraryItemsResponse,
    ListPlaylistsResponse,
    PlaylistResponse,
    ReorderPlaylistTracksRequest,
    UpdatePlaylistRequest,
)
from backend.application.library.use_cases.items import LibraryItemUseCases
from backend.application.library.use_cases.playlists import LibraryPlaylistUseCases
from backend.application.discovery.use_cases.events_and_recommendations import DiscoveryUseCases
from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.domain.identity.repositories import IdentityUserReadModel
from backend.domain.library.repositories import LibraryItemReadModel, PlaylistReadModel
from backend.infrastructure.cache.response_cache import ApiResponseCache

router = APIRouter(prefix="/library", tags=["library"])


@router.post("/playlists", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    payload: CreatePlaylistRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryPlaylistUseCases = Depends(get_library_playlist_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
    response_cache: ApiResponseCache = Depends(get_api_response_cache),
) -> PlaylistResponse:
    try:
        result = await use_cases.create_playlist(
            user.id,
            title=payload.title,
            description=payload.description,
            visibility=payload.visibility,
        )
        await db_session.commit()
        if result.visibility == "public":
            await _invalidate_public_playlist_cache(response_cache, playlist_id=result.id)
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return _to_playlist_response(result)


@router.patch("/playlists/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: UUID,
    payload: UpdatePlaylistRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryPlaylistUseCases = Depends(get_library_playlist_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
    response_cache: ApiResponseCache = Depends(get_api_response_cache),
) -> PlaylistResponse:
    try:
        existing_playlist = await use_cases.get_my_playlist(user.id, playlist_id=playlist_id)
        result = await use_cases.update_playlist(
            user.id,
            playlist_id=playlist_id,
            title=payload.title,
            description=payload.description,
            visibility=payload.visibility,
        )
        await db_session.commit()
        if existing_playlist.visibility != result.visibility:
            await _invalidate_public_playlist_cache(response_cache, playlist_id=result.id)
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_playlist_response(result)


@router.delete("/playlists/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryPlaylistUseCases = Depends(get_library_playlist_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
    response_cache: ApiResponseCache = Depends(get_api_response_cache),
) -> Response:
    try:
        await use_cases.delete_playlist(user.id, playlist_id=playlist_id)
        await db_session.commit()
        await _invalidate_public_playlist_cache(response_cache, playlist_id=playlist_id)
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_404_NOT_FOUND, "not_found", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/playlists/me", response_model=ListPlaylistsResponse)
async def list_my_playlists(
    limit: int = Query(default=20),
    offset: int = Query(default=0),
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryPlaylistUseCases = Depends(get_library_playlist_use_cases),
) -> ListPlaylistsResponse:
    try:
        items = await use_cases.list_my_playlists(user.id, limit=limit, offset=offset)
    except ValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return ListPlaylistsResponse(items=[_to_playlist_response(item) for item in items])


@router.get("/playlists/me/{playlist_id}", response_model=PlaylistResponse)
async def get_my_playlist(
    playlist_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryPlaylistUseCases = Depends(get_library_playlist_use_cases),
) -> PlaylistResponse:
    try:
        item = await use_cases.get_my_playlist(user.id, playlist_id=playlist_id)
    except ValidationError as exc:
        raise _http_error(status.HTTP_404_NOT_FOUND, "not_found", exc.message) from exc
    except AuthorizationError as exc:
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_playlist_response(item)


@router.post("/playlists/{playlist_id}/tracks", response_model=PlaylistResponse)
async def add_playlist_track(
    playlist_id: UUID,
    payload: AddPlaylistTrackRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryPlaylistUseCases = Depends(get_library_playlist_use_cases),
    discovery_use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> PlaylistResponse:
    try:
        track_id = UUID(payload.track_id)
        result = await use_cases.add_track(
            user.id,
            playlist_id=playlist_id,
            track_id=track_id,
            position=payload.position,
        )
        await discovery_use_cases.record_playlist_add_event(user.id, track_id=track_id)
        await db_session.commit()
    except ValueError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", "Track id should be a valid UUID value.") from exc
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    except IntegrityError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_409_CONFLICT, "conflict_error", "Playlist track constraints violated.") from exc
    return _to_playlist_response(result)


@router.delete("/playlists/{playlist_id}/tracks/{track_id}", response_model=PlaylistResponse)
async def remove_playlist_track(
    playlist_id: UUID,
    track_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryPlaylistUseCases = Depends(get_library_playlist_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> PlaylistResponse:
    try:
        result = await use_cases.remove_track(user.id, playlist_id=playlist_id, track_id=track_id)
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_playlist_response(result)


@router.put("/playlists/{playlist_id}/tracks/reorder", response_model=PlaylistResponse)
async def reorder_playlist_tracks(
    playlist_id: UUID,
    payload: ReorderPlaylistTracksRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryPlaylistUseCases = Depends(get_library_playlist_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> PlaylistResponse:
    try:
        result = await use_cases.reorder_tracks(
            user.id,
            playlist_id=playlist_id,
            track_ids=[UUID(item) for item in payload.track_ids],
        )
        await db_session.commit()
    except ValueError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", "Track ids should be valid UUID values.") from exc
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_playlist_response(result)


@router.get("/playlists/public", response_model=ListPlaylistsResponse)
async def list_public_playlists(
    limit: int = Query(default=20),
    offset: int = Query(default=0),
    use_cases: LibraryPlaylistUseCases = Depends(get_library_playlist_use_cases),
    response_cache: ApiResponseCache = Depends(get_api_response_cache),
) -> ListPlaylistsResponse:
    cache_key = response_cache.build_key(
        "library:playlists:public:list",
        limit=limit,
        offset=offset,
    )
    cached_payload = await response_cache.get_json(cache_key)
    if cached_payload is not None:
        return ListPlaylistsResponse.model_validate(cached_payload)
    try:
        items = await use_cases.list_public_playlists(limit=limit, offset=offset)
    except ValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    response = ListPlaylistsResponse(items=[_to_playlist_response(item) for item in items])
    await response_cache.set_json(
        key=cache_key,
        payload=response.model_dump(mode="json"),
        ttl_seconds=response_cache.ttl_for_public_playlist_reads(),
    )
    return response


@router.get("/playlists/public/{playlist_id}", response_model=PlaylistResponse)
async def get_public_playlist(
    playlist_id: UUID,
    use_cases: LibraryPlaylistUseCases = Depends(get_library_playlist_use_cases),
    response_cache: ApiResponseCache = Depends(get_api_response_cache),
) -> PlaylistResponse:
    cache_key = response_cache.build_key("library:playlists:public:get", playlist_id=playlist_id)
    cached_payload = await response_cache.get_json(cache_key)
    if cached_payload is not None:
        return PlaylistResponse.model_validate(cached_payload)
    try:
        item = await use_cases.get_public_playlist(playlist_id)
    except ValidationError as exc:
        raise _http_error(status.HTTP_404_NOT_FOUND, "not_found", exc.message) from exc
    response = _to_playlist_response(item)
    await response_cache.set_json(
        key=cache_key,
        payload=response.model_dump(mode="json"),
        ttl_seconds=response_cache.ttl_for_public_playlist_reads(),
    )
    return response


@router.post("/items", response_model=LibraryItemResponse, status_code=status.HTTP_201_CREATED)
async def add_library_item(
    payload: AddLibraryItemRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryItemUseCases = Depends(get_library_item_use_cases),
    discovery_use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> LibraryItemResponse:
    try:
        item_id = UUID(payload.item_id)
        result = await use_cases.add_item(
            user.id,
            item_type=payload.item_type,
            item_id=item_id,
            section=payload.section,
        )
        await discovery_use_cases.record_save_events(
            user.id,
            item_type=payload.item_type,
            item_id=item_id,
        )
        await db_session.commit()
    except ValueError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", "Item id should be a valid UUID value.") from exc
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except IntegrityError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_409_CONFLICT, "conflict_error", "Library item constraints violated.") from exc
    return _to_library_item_response(result)


@router.delete("/items/{item_type}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_library_item(
    item_type: str,
    item_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryItemUseCases = Depends(get_library_item_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> Response:
    try:
        await use_cases.remove_item(user.id, item_type=item_type, item_id=item_id)
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_404_NOT_FOUND, "not_found", exc.message) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/items", response_model=ListLibraryItemsResponse)
async def list_library_items(
    section: str | None = Query(default=None),
    item_type: str | None = Query(default=None),
    limit: int = Query(default=20),
    offset: int = Query(default=0),
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: LibraryItemUseCases = Depends(get_library_item_use_cases),
) -> ListLibraryItemsResponse:
    try:
        items = await use_cases.list_items(
            user.id,
            section=section,
            item_type=item_type,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return ListLibraryItemsResponse(items=[_to_library_item_response(item) for item in items])


def _to_playlist_response(item: PlaylistReadModel) -> PlaylistResponse:
    return PlaylistResponse(
        id=str(item.id),
        owner_user_id=str(item.owner_user_id),
        title=item.title,
        description=item.description,
        visibility=item.visibility,
        likes_count=item.likes_count,
        comments_count=item.comments_count,
        created_at=item.created_at,
        track_items=[
            {
                "track_id": str(track.track_id),
                "added_by_user_id": str(track.added_by_user_id),
                "position": track.position,
                "added_at": track.added_at,
            }
            for track in item.track_items
        ],
    )


def _to_library_item_response(item: LibraryItemReadModel) -> LibraryItemResponse:
    return LibraryItemResponse(
        id=str(item.id),
        user_id=str(item.user_id),
        item_type=item.item_type,
        item_id=str(item.item_id),
        section=item.section,
        created_at=item.created_at,
    )


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


async def _invalidate_public_playlist_cache(response_cache: ApiResponseCache, *, playlist_id: UUID) -> None:
    await response_cache.delete_namespace("library:playlists:public:list")
    detail_key = response_cache.build_key("library:playlists:public:get", playlist_id=playlist_id)
    await response_cache.delete_key(detail_key)
