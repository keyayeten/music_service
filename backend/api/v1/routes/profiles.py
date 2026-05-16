from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.deps import get_current_identity_user, get_db_session, get_identity_profiles_use_cases
from backend.api.v1.schemas.profiles import MyProfileResponse, UpdateMyProfileRequest
from backend.application.identity.use_cases.profiles import IdentityProfileResult, IdentityProfilesUseCases
from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.domain.identity.repositories import IdentityUserReadModel

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/me", response_model=MyProfileResponse)
def get_my_profile(
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: IdentityProfilesUseCases = Depends(get_identity_profiles_use_cases),
) -> MyProfileResponse:
    try:
        profile = use_cases.get_my_profile(user.id)
    except ValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    return _to_response(profile)


@router.patch("/me", response_model=MyProfileResponse)
def update_my_profile(
    payload: UpdateMyProfileRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: IdentityProfilesUseCases = Depends(get_identity_profiles_use_cases),
    db_session: Session = Depends(get_db_session),
) -> MyProfileResponse:
    try:
        profile = use_cases.update_my_profile(
            user.id,
            display_name=payload.display_name,
            bio=payload.bio,
            country_code=payload.country_code,
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
        raise _http_error(status.HTTP_409_CONFLICT, "conflict_error", "Profile constraints violated.") from exc
    return _to_response(profile)


def _to_response(profile: IdentityProfileResult) -> MyProfileResponse:
    composer_profile_payload = None
    if profile.composer_profile is not None:
        composer_profile_payload = {
            "id": str(profile.composer_profile.id),
            "display_name": profile.composer_profile.display_name,
            "bio": profile.composer_profile.bio,
            "country_code": profile.composer_profile.country_code,
            "verified": profile.composer_profile.verified,
        }
    return MyProfileResponse(
        id=str(profile.user.id),
        email=profile.user.email,
        username=profile.user.username,
        status=profile.user.status,
        roles=profile.roles,
        composer_profile=composer_profile_payload,
    )


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
