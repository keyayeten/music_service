from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from redis import Redis
from sqlalchemy.orm import Session

from backend.application.identity.use_cases.auth import IdentityAuthUseCases
from backend.application.identity.use_cases.profiles import IdentityProfilesUseCases
from backend.config.settings import Settings, get_settings
from backend.domain.common.exceptions import AuthenticationError
from backend.domain.identity.repositories import IdentityUserReadModel
from backend.infrastructure.persistence.repositories.identity_auth import SqlAlchemyIdentityAuthRepository
from backend.infrastructure.cache.redis_client import get_redis_client
from backend.infrastructure.persistence.database import get_session


def get_db_session() -> Generator[Session, None, None]:
    yield from get_session()


def get_app_settings() -> Settings:
    return get_settings()


def get_cache_client() -> Redis:
    return get_redis_client()


def get_identity_auth_use_cases(db_session: Session = Depends(get_db_session)) -> IdentityAuthUseCases:
    settings = get_settings()
    repository = SqlAlchemyIdentityAuthRepository(db_session)
    return IdentityAuthUseCases(
        repository=repository,
        jwt_secret=settings.jwt_secret,
        jwt_access_ttl_minutes=settings.jwt_access_ttl_minutes,
        jwt_refresh_ttl_minutes=settings.jwt_refresh_ttl_minutes,
    )


def get_identity_profiles_use_cases(db_session: Session = Depends(get_db_session)) -> IdentityProfilesUseCases:
    repository = SqlAlchemyIdentityAuthRepository(db_session)
    return IdentityProfilesUseCases(repository=repository)


def get_current_identity_user(
    authorization: str | None = Header(default=None),
    auth_use_cases: IdentityAuthUseCases = Depends(get_identity_auth_use_cases),
) -> IdentityUserReadModel:
    access_token = extract_bearer_token(authorization)
    try:
        return auth_use_cases.get_current_user(access_token)
    except AuthenticationError as exc:
        raise _http_error(status.HTTP_401_UNAUTHORIZED, "authentication_error", exc.message) from exc


def get_user_roles(db_session: Session, user_id: str) -> list[str]:
    repository = SqlAlchemyIdentityAuthRepository(db_session)
    return repository.get_user_role_codes(UUID(user_id))


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _http_error(status.HTTP_401_UNAUTHORIZED, "authentication_error", "Bearer token is required.")
    return authorization.split(" ", 1)[1].strip()


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
