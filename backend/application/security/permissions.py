from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from backend.domain.common.exceptions import AuthorizationError

MODERATION_ROLES = {"admin", "moderator"}
COMPOSER_ROLE = "composer"
USER_ROLE = "user"


def ensure_any_role(actor_roles: Iterable[str], *, allowed_roles: set[str], message: str) -> None:
    if not any(role in allowed_roles for role in actor_roles):
        raise AuthorizationError(message)


def ensure_composer_access(
    actor_user_id: UUID,
    *,
    actor_roles: Iterable[str],
    composer_profile_id: UUID | None,
) -> UUID:
    if COMPOSER_ROLE not in set(actor_roles):
        raise AuthorizationError("Composer role is required.")
    if composer_profile_id is None:
        raise AuthorizationError("Composer profile is required.")
    return composer_profile_id
