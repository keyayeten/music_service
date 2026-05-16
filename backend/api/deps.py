from collections.abc import Generator
from uuid import UUID

from fastapi import Depends
from redis import Redis
from sqlalchemy.orm import Session

from backend.application.identity.use_cases.auth import IdentityAuthUseCases
from backend.config.settings import Settings, get_settings
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


def get_user_roles(db_session: Session, user_id: str) -> list[str]:
    repository = SqlAlchemyIdentityAuthRepository(db_session)
    return repository.get_user_role_codes(UUID(user_id))
