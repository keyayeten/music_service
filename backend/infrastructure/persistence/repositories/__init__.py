"""Repository implementations backed by persistence layer."""

from backend.infrastructure.persistence.repositories.catalog import SqlAlchemyCatalogRepository
from backend.infrastructure.persistence.repositories.identity_auth import (
    SqlAlchemyIdentityAuthRepository,
)
from backend.infrastructure.persistence.repositories.library import SqlAlchemyLibraryRepository
from backend.infrastructure.persistence.repositories.moderation import (
    SqlAlchemyModerationRepository,
)
from backend.infrastructure.persistence.repositories.social import SqlAlchemySocialRepository

__all__ = [
    "SqlAlchemyIdentityAuthRepository",
    "SqlAlchemyCatalogRepository",
    "SqlAlchemyLibraryRepository",
    "SqlAlchemyModerationRepository",
    "SqlAlchemySocialRepository",
]
