from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class IdentityUserReadModel:
    id: UUID
    email: str
    username: str
    status: str


@dataclass(frozen=True)
class IdentityUserAuthModel:
    id: UUID
    email: str
    username: str
    password_hash: str
    status: str


class IdentityUserRepository(Protocol):
    def get_by_id(self, user_id: UUID) -> IdentityUserReadModel | None:
        """Return user projection or None if not found."""


class IdentityAuthRepository(Protocol):
    def get_user_by_id(self, user_id: UUID) -> IdentityUserReadModel | None:
        """Return user projection with public profile fields."""

    def get_user_auth_by_login(self, login: str) -> IdentityUserAuthModel | None:
        """Lookup user by username or email with password hash."""

    def create_user(self, email: str, username: str, password_hash: str, status: str = "active") -> IdentityUserReadModel:
        """Create a new identity user."""

    def get_user_by_email(self, email: str) -> IdentityUserReadModel | None:
        """Find user by email."""

    def get_user_by_username(self, username: str) -> IdentityUserReadModel | None:
        """Find user by username."""

    def ensure_roles_seeded(self) -> None:
        """Ensure base role records exist in DB."""

    def get_role_id_by_code(self, code: str) -> int | None:
        """Resolve role id by unique code."""

    def assign_role(self, user_id: UUID, role_id: int) -> None:
        """Assign role to user if not yet assigned."""

    def get_user_role_codes(self, user_id: UUID) -> list[str]:
        """List user role codes."""
