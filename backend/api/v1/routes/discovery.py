from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.deps import get_discovery_use_cases, get_optional_identity_user
from backend.api.v1.schemas.discovery import ListRecommendedTracksResponse, RecommendedTrackItem
from backend.application.discovery.use_cases.events_and_recommendations import DiscoveryUseCases
from backend.domain.common.exceptions import ValidationError
from backend.domain.identity.repositories import IdentityUserReadModel

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.get("/recommendations/tracks", response_model=ListRecommendedTracksResponse)
async def list_track_recommendations(
    limit: int = Query(default=20),
    user: IdentityUserReadModel | None = Depends(get_optional_identity_user),
    use_cases: DiscoveryUseCases = Depends(get_discovery_use_cases),
) -> ListRecommendedTracksResponse:
    try:
        items = await use_cases.list_recommended_tracks(
            actor_user_id=user.id if user else None,
            limit=limit,
        )
    except ValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return ListRecommendedTracksResponse(
        items=[
            RecommendedTrackItem(
                track_id=str(item.track_id),
                score=item.score,
                source=item.source,
            )
            for item in items
        ]
    )


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
