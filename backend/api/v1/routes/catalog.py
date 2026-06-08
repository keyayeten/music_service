from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import (
    get_api_response_cache,
    get_catalog_album_use_cases,
    get_catalog_track_use_cases,
    get_current_identity_user,
    get_db_session,
    get_discovery_use_cases,
    get_optional_identity_user,
    get_user_roles,
)
from backend.api.v1.schemas.catalog import (
    AlbumResponse,
    CreateAlbumRequest,
    CreateTrackRequest,
    ListAlbumsResponse,
    ListTracksResponse,
    ModerateAlbumRequest,
    ModerateTrackRequest,
    ReplaceAlbumTracksRequest,
    ReplaceTrackAuthorsRequest,
    TrackResponse,
    UpdateAlbumRequest,
    UpdateTrackRequest,
)
from backend.api.v1.schemas.discovery import ExternalLinkClickResponse
from backend.application.catalog.use_cases.albums import CatalogAlbumUseCases
from backend.application.catalog.use_cases.tracks import CatalogTrackUseCases
from backend.application.discovery.use_cases.events_and_recommendations import DiscoveryUseCases
from backend.domain.catalog.repositories import AlbumReadModel, TrackReadModel
from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.domain.identity.repositories import IdentityUserReadModel
from backend.infrastructure.cache.response_cache import ApiResponseCache

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post("/tracks", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
async def create_track(
    payload: CreateTrackRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> TrackResponse:
    try:
        result = await use_cases.create_track(
            user.id,
            title=payload.title,
            description=payload.description,
            duration_seconds=payload.duration_seconds,
        )
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    except IntegrityError as exc:
        await db_session.rollback()
        raise _http_error(
            status.HTTP_409_CONFLICT, "conflict_error", "Track constraints violated."
        ) from exc
    return _to_track_response(result)


@router.patch("/tracks/{track_id}", response_model=TrackResponse)
async def update_track(
    track_id: UUID,
    payload: UpdateTrackRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> TrackResponse:
    try:
        result = await use_cases.update_track(
            user.id,
            track_id=track_id,
            title=payload.title,
            description=payload.description,
            duration_seconds=payload.duration_seconds,
        )
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_track_response(result)


@router.put("/tracks/{track_id}/authors", response_model=TrackResponse)
async def replace_track_authors(
    track_id: UUID,
    payload: ReplaceTrackAuthorsRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> TrackResponse:
    try:
        result = await use_cases.set_track_authors(
            user.id,
            track_id=track_id,
            author_profile_ids=[UUID(item) for item in payload.author_profile_ids],
        )
        await db_session.commit()
    except ValueError as exc:
        await db_session.rollback()
        raise _http_error(
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
            "Author ids should be valid UUID values.",
        ) from exc
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_track_response(result)


@router.post("/tracks/{track_id}/publish", response_model=TrackResponse)
async def publish_track(
    track_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> TrackResponse:
    try:
        result = await use_cases.publish_track(user.id, track_id=track_id)
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_track_response(result)


@router.post("/tracks/{track_id}/submit-review", response_model=TrackResponse)
async def submit_track_review(
    track_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> TrackResponse:
    try:
        result = await use_cases.submit_track_for_review(user.id, track_id=track_id)
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_track_response(result)


@router.post("/tracks/{track_id}/moderate", response_model=TrackResponse)
async def moderate_track(
    track_id: UUID,
    payload: ModerateTrackRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> TrackResponse:
    try:
        roles = await get_user_roles(db_session, str(user.id))
        result = await use_cases.moderate_track(
            roles, track_id=track_id, target_status=payload.target_status
        )
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_track_response(result)


@router.get("/tracks", response_model=ListTracksResponse)
async def list_tracks(
    status_filter: str | None = Query(default=None, alias="status"),
    genre: str | None = Query(default=None),
    author_id: UUID | None = Query(default=None),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    user: IdentityUserReadModel | None = Depends(get_optional_identity_user),
    discovery_use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> ListTracksResponse:
    try:
        items = await use_cases.list_tracks(
            status=status_filter,
            genre_code=genre,
            author_id=author_id,
            include_unpublished=False,
        )
        if user is not None and items:
            await discovery_use_cases.record_view_events(
                user.id,
                track_ids=[item.id for item in items],
            )
            await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return ListTracksResponse(items=[_to_track_response(item) for item in items])


@router.get("/tracks/{track_id}", response_model=TrackResponse)
async def get_track(
    track_id: UUID,
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    user: IdentityUserReadModel | None = Depends(get_optional_identity_user),
    discovery_use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> TrackResponse:
    try:
        item = await use_cases.get_track(track_id, include_unpublished=False)
        if user is not None:
            await discovery_use_cases.record_view_events(user.id, track_ids=[item.id])
            await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_404_NOT_FOUND, "not_found", exc.message) from exc
    return _to_track_response(item)


@router.post("/external-links/{external_link_id}/click", response_model=ExternalLinkClickResponse)
async def click_external_link(
    external_link_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    discovery_use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> ExternalLinkClickResponse:
    try:
        await discovery_use_cases.record_external_click_event(
            user.id,
            external_link_id=external_link_id,
        )
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return ExternalLinkClickResponse(status="recorded", external_link_id=str(external_link_id))


@router.post("/albums", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
async def create_album(
    payload: CreateAlbumRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> AlbumResponse:
    try:
        result = await use_cases.create_album(
            user.id,
            title=payload.title,
            description=payload.description,
            release_date=payload.release_date,
        )
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_album_response(result)


@router.patch("/albums/{album_id}", response_model=AlbumResponse)
async def update_album(
    album_id: UUID,
    payload: UpdateAlbumRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> AlbumResponse:
    try:
        result = await use_cases.update_album(
            user.id,
            album_id=album_id,
            title=payload.title,
            description=payload.description,
            release_date=payload.release_date,
        )
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_album_response(result)


@router.put("/albums/{album_id}/tracks", response_model=AlbumResponse)
async def replace_album_tracks(
    album_id: UUID,
    payload: ReplaceAlbumTracksRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> AlbumResponse:
    try:
        result = await use_cases.replace_album_tracks(
            user.id,
            album_id=album_id,
            track_ids=[UUID(item) for item in payload.track_ids],
        )
        await db_session.commit()
    except ValueError as exc:
        await db_session.rollback()
        raise _http_error(
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
            "Track ids should be valid UUID values.",
        ) from exc
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    except IntegrityError as exc:
        await db_session.rollback()
        raise _http_error(
            status.HTTP_409_CONFLICT, "conflict_error", "Album track constraints violated."
        ) from exc
    return _to_album_response(result)


@router.post("/albums/{album_id}/publish", response_model=AlbumResponse)
async def publish_album(
    album_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> AlbumResponse:
    try:
        result = await use_cases.publish_album(user.id, album_id=album_id)
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_album_response(result)


@router.post("/albums/{album_id}/submit-review", response_model=AlbumResponse)
async def submit_album_review(
    album_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> AlbumResponse:
    try:
        result = await use_cases.submit_album_for_review(user.id, album_id=album_id)
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_album_response(result)


@router.post("/albums/{album_id}/moderate", response_model=AlbumResponse)
async def moderate_album(
    album_id: UUID,
    payload: ModerateAlbumRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> AlbumResponse:
    try:
        roles = await get_user_roles(db_session, str(user.id))
        result = await use_cases.moderate_album(
            roles, album_id=album_id, target_status=payload.target_status
        )
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_album_response(result)


@router.get("/albums", response_model=ListAlbumsResponse)
async def list_albums(
    status_filter: str | None = Query(default=None, alias="status"),
    owner_composer_id: UUID | None = Query(default=None),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    response_cache: ApiResponseCache = Depends(get_api_response_cache),
) -> ListAlbumsResponse:
    cache_key = response_cache.build_key(
        "catalog:albums:list",
        status=status_filter,
        owner_composer_id=owner_composer_id,
    )
    cached_payload = await response_cache.get_json(cache_key)
    if cached_payload is not None:
        return ListAlbumsResponse.model_validate(cached_payload)
    try:
        items = await use_cases.list_albums(
            status=status_filter,
            owner_composer_id=owner_composer_id,
            include_unpublished=False,
        )
    except ValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    response = ListAlbumsResponse(items=[_to_album_response(item) for item in items])
    await response_cache.set_json(
        key=cache_key,
        payload=response.model_dump(mode="json"),
        ttl_seconds=response_cache.ttl_for_catalog_reads(),
    )
    return response


@router.get("/albums/{album_id}", response_model=AlbumResponse)
async def get_album(
    album_id: UUID,
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    response_cache: ApiResponseCache = Depends(get_api_response_cache),
) -> AlbumResponse:
    cache_key = response_cache.build_key("catalog:albums:get", album_id=album_id)
    cached_payload = await response_cache.get_json(cache_key)
    if cached_payload is not None:
        return AlbumResponse.model_validate(cached_payload)
    try:
        item = await use_cases.get_album(album_id, include_unpublished=False)
    except ValidationError as exc:
        raise _http_error(status.HTTP_404_NOT_FOUND, "not_found", exc.message) from exc
    response = _to_album_response(item)
    await response_cache.set_json(
        key=cache_key,
        payload=response.model_dump(mode="json"),
        ttl_seconds=response_cache.ttl_for_catalog_reads(),
    )
    return response


def _to_track_response(track: TrackReadModel) -> TrackResponse:
    return TrackResponse(
        id=str(track.id),
        title=track.title,
        description=track.description,
        status=track.status,
        duration_seconds=track.duration_seconds,
        plays_count=track.plays_count,
        likes_count=track.likes_count,
        comments_count=track.comments_count,
        published_at=track.published_at,
        created_at=track.created_at,
        authors=[
            {
                "composer_profile_id": str(author.composer_profile_id),
                "contribution_role": author.contribution_role,
                "position": author.position,
            }
            for author in track.authors
        ],
        genre_codes=track.genre_codes,
    )


def _to_album_response(album: AlbumReadModel) -> AlbumResponse:
    return AlbumResponse(
        id=str(album.id),
        owner_composer_id=str(album.owner_composer_id),
        title=album.title,
        description=album.description,
        status=album.status,
        release_date=album.release_date,
        likes_count=album.likes_count,
        comments_count=album.comments_count,
        created_at=album.created_at,
        track_items=[
            {"track_id": str(item.track_id), "position": item.position}
            for item in album.track_items
        ],
    )


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
