from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class IdentityUserReadModel:
    id: UUID
    email: str
    username: str


class IdentityUserRepository(Protocol):
    def get_by_id(self, user_id: UUID) -> IdentityUserReadModel | None:
        """Return user projection or None if not found."""
