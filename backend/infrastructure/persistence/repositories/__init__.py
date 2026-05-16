"""Repository implementations backed by persistence layer."""

from backend.infrastructure.persistence.repositories.identity_auth import SqlAlchemyIdentityAuthRepository

__all__ = ["SqlAlchemyIdentityAuthRepository"]
