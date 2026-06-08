from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import (
    get_current_identity_user,
    get_db_session,
    get_identity_auth_use_cases,
    get_user_roles,
)
from backend.api.v1.schemas.auth import (
    AuthSuccessResponse,
    LoginRequest,
    RefreshTokenRequest,
    SignupRequest,
    UserProfileResponse,
)
from backend.application.identity.use_cases.auth import AuthResult, IdentityAuthUseCases
from backend.domain.common.exceptions import AuthenticationError, ConflictError, ValidationError
from backend.domain.identity.repositories import IdentityUserReadModel

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthSuccessResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    auth_use_cases: IdentityAuthUseCases = Depends(get_identity_auth_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> AuthSuccessResponse:
    try:
        result = await auth_use_cases.signup(payload.email, payload.username, payload.password)
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except ConflictError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_409_CONFLICT, "conflict_error", exc.message) from exc
    except IntegrityError as exc:
        await db_session.rollback()
        raise _http_error(
            status.HTTP_409_CONFLICT, "conflict_error", "User already exists."
        ) from exc
    roles = await get_user_roles(db_session, str(result.user.id))
    return _to_auth_response(result, roles)


@router.post("/login", response_model=AuthSuccessResponse)
async def login(
    payload: LoginRequest,
    auth_use_cases: IdentityAuthUseCases = Depends(get_identity_auth_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> AuthSuccessResponse:
    try:
        result = await auth_use_cases.login(payload.login, payload.password)
    except ValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthenticationError as exc:
        raise _http_error(
            status.HTTP_401_UNAUTHORIZED, "authentication_error", exc.message
        ) from exc
    roles = await get_user_roles(db_session, str(result.user.id))
    return _to_auth_response(result, roles)


@router.post("/refresh", response_model=AuthSuccessResponse)
async def refresh(
    payload: RefreshTokenRequest,
    auth_use_cases: IdentityAuthUseCases = Depends(get_identity_auth_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> AuthSuccessResponse:
    try:
        result = await auth_use_cases.refresh(payload.refresh_token)
    except AuthenticationError as exc:
        raise _http_error(
            status.HTTP_401_UNAUTHORIZED, "authentication_error", exc.message
        ) from exc
    roles = await get_user_roles(db_session, str(result.user.id))
    return _to_auth_response(result, roles)


@router.get("/me", response_model=UserProfileResponse)
async def me(
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        status=user.status,
        roles=await get_user_roles(db_session, str(user.id)),
    )


def _to_auth_response(result: AuthResult, roles: list[str]) -> AuthSuccessResponse:
    return AuthSuccessResponse(
        user=UserProfileResponse(
            id=str(result.user.id),
            email=result.user.email,
            username=result.user.username,
            status=result.user.status,
            roles=roles,
        ),
        tokens={
            "access_token": result.access_token,
            "refresh_token": result.refresh_token,
            "token_type": result.token_type,
            "access_expires_in": result.access_expires_in,
            "refresh_expires_in": result.refresh_expires_in,
        },
    )


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
