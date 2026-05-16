from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.deps import (
    get_catalog_album_use_cases,
    get_catalog_track_use_cases,
    get_current_identity_user,
    get_discovery_use_cases,
    get_db_session,
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

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post("/tracks", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
def create_track(
    payload: CreateTrackRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: Session = Depends(get_db_session),
) -> TrackResponse:
    try:
        result = use_cases.create_track(
            user.id,
            title=payload.title,
            description=payload.description,
            duration_seconds=payload.duration_seconds,
        )
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    except IntegrityError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_409_CONFLICT, "conflict_error", "Track constraints violated.") from exc
    return _to_track_response(result)


@router.patch("/tracks/{track_id}", response_model=TrackResponse)
def update_track(
    track_id: UUID,
    payload: UpdateTrackRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: Session = Depends(get_db_session),
) -> TrackResponse:
    try:
        result = use_cases.update_track(
            user.id,
            track_id=track_id,
            title=payload.title,
            description=payload.description,
            duration_seconds=payload.duration_seconds,
        )
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_track_response(result)


@router.put("/tracks/{track_id}/authors", response_model=TrackResponse)
def replace_track_authors(
    track_id: UUID,
    payload: ReplaceTrackAuthorsRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: Session = Depends(get_db_session),
) -> TrackResponse:
    try:
        result = use_cases.set_track_authors(
            user.id,
            track_id=track_id,
            author_profile_ids=[UUID(item) for item in payload.author_profile_ids],
        )
        db_session.commit()
    except ValueError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", "Author ids should be valid UUID values.") from exc
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_track_response(result)


@router.post("/tracks/{track_id}/publish", response_model=TrackResponse)
def publish_track(
    track_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: Session = Depends(get_db_session),
) -> TrackResponse:
    try:
        result = use_cases.publish_track(user.id, track_id=track_id)
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_track_response(result)


@router.post("/tracks/{track_id}/submit-review", response_model=TrackResponse)
def submit_track_review(
    track_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: Session = Depends(get_db_session),
) -> TrackResponse:
    try:
        result = use_cases.submit_track_for_review(user.id, track_id=track_id)
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_track_response(result)


@router.post("/tracks/{track_id}/moderate", response_model=TrackResponse)
def moderate_track(
    track_id: UUID,
    payload: ModerateTrackRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    db_session: Session = Depends(get_db_session),
) -> TrackResponse:
    try:
        roles = get_user_roles(db_session, str(user.id))
        result = use_cases.moderate_track(roles, track_id=track_id, target_status=payload.target_status)
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_track_response(result)


@router.get("/tracks", response_model=ListTracksResponse)
def list_tracks(
    status_filter: str | None = Query(default=None, alias="status"),
    genre: str | None = Query(default=None),
    author_id: UUID | None = Query(default=None),
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    user: IdentityUserReadModel | None = Depends(get_optional_identity_user),
    discovery_use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
    db_session: Session = Depends(get_db_session),
) -> ListTracksResponse:
    try:
        items = use_cases.list_tracks(
            status=status_filter,
            genre_code=genre,
            author_id=author_id,
            include_unpublished=False,
        )
        if user is not None and items:
            discovery_use_cases.record_view_events(
                user.id,
                track_ids=[item.id for item in items],
            )
            db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return ListTracksResponse(items=[_to_track_response(item) for item in items])


@router.get("/tracks/{track_id}", response_model=TrackResponse)
def get_track(
    track_id: UUID,
    use_cases: CatalogTrackUseCases = Depends(get_catalog_track_use_cases),
    user: IdentityUserReadModel | None = Depends(get_optional_identity_user),
    discovery_use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
    db_session: Session = Depends(get_db_session),
) -> TrackResponse:
    try:
        item = use_cases.get_track(track_id, include_unpublished=False)
        if user is not None:
            discovery_use_cases.record_view_events(user.id, track_ids=[item.id])
            db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_404_NOT_FOUND, "not_found", exc.message) from exc
    return _to_track_response(item)


@router.post("/external-links/{external_link_id}/click", response_model=ExternalLinkClickResponse)
def click_external_link(
    external_link_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    discovery_use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
    db_session: Session = Depends(get_db_session),
) -> ExternalLinkClickResponse:
    try:
        discovery_use_cases.record_external_click_event(
            user.id,
            external_link_id=external_link_id,
        )
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return ExternalLinkClickResponse(status="recorded", external_link_id=str(external_link_id))


@router.post("/albums", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
def create_album(
    payload: CreateAlbumRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: Session = Depends(get_db_session),
) -> AlbumResponse:
    try:
        result = use_cases.create_album(
            user.id,
            title=payload.title,
            description=payload.description,
            release_date=payload.release_date,
        )
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_album_response(result)


@router.patch("/albums/{album_id}", response_model=AlbumResponse)
def update_album(
    album_id: UUID,
    payload: UpdateAlbumRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: Session = Depends(get_db_session),
) -> AlbumResponse:
    try:
        result = use_cases.update_album(
            user.id,
            album_id=album_id,
            title=payload.title,
            description=payload.description,
            release_date=payload.release_date,
        )
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_album_response(result)


@router.put("/albums/{album_id}/tracks", response_model=AlbumResponse)
def replace_album_tracks(
    album_id: UUID,
    payload: ReplaceAlbumTracksRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: Session = Depends(get_db_session),
) -> AlbumResponse:
    try:
        result = use_cases.replace_album_tracks(
            user.id,
            album_id=album_id,
            track_ids=[UUID(item) for item in payload.track_ids],
        )
        db_session.commit()
    except ValueError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", "Track ids should be valid UUID values.") from exc
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    except IntegrityError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_409_CONFLICT, "conflict_error", "Album track constraints violated.") from exc
    return _to_album_response(result)


@router.post("/albums/{album_id}/publish", response_model=AlbumResponse)
def publish_album(
    album_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: Session = Depends(get_db_session),
) -> AlbumResponse:
    try:
        result = use_cases.publish_album(user.id, album_id=album_id)
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_album_response(result)


@router.post("/albums/{album_id}/submit-review", response_model=AlbumResponse)
def submit_album_review(
    album_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: Session = Depends(get_db_session),
) -> AlbumResponse:
    try:
        result = use_cases.submit_album_for_review(user.id, album_id=album_id)
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_album_response(result)


@router.post("/albums/{album_id}/moderate", response_model=AlbumResponse)
def moderate_album(
    album_id: UUID,
    payload: ModerateAlbumRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
    db_session: Session = Depends(get_db_session),
) -> AlbumResponse:
    try:
        roles = get_user_roles(db_session, str(user.id))
        result = use_cases.moderate_album(roles, album_id=album_id, target_status=payload.target_status)
        db_session.commit()
    except ValidationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_album_response(result)


@router.get("/albums", response_model=ListAlbumsResponse)
def list_albums(
    status_filter: str | None = Query(default=None, alias="status"),
    owner_composer_id: UUID | None = Query(default=None),
    use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases),
) -> ListAlbumsResponse:
    try:
        items = use_cases.list_albums(
            status=status_filter,
            owner_composer_id=owner_composer_id,
            include_unpublished=False,
        )
    except ValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return ListAlbumsResponse(items=[_to_album_response(item) for item in items])


@router.get("/albums/{album_id}", response_model=AlbumResponse)
def get_album(album_id: UUID, use_cases: CatalogAlbumUseCases = Depends(get_catalog_album_use_cases)) -> AlbumResponse:
    try:
        item = use_cases.get_album(album_id, include_unpublished=False)
    except ValidationError as exc:
        raise _http_error(status.HTTP_404_NOT_FOUND, "not_found", exc.message) from exc
    return _to_album_response(item)


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
        track_items=[{"track_id": str(item.track_id), "position": item.position} for item in album.track_items],
    )


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
