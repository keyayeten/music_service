from __future__ import annotations

from datetime import date
from uuid import UUID

from backend.domain.catalog.repositories import AlbumListFilter, AlbumReadModel, CatalogRepository
from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.application.security.permissions import MODERATION_ROLES, ensure_composer_access

ALBUM_STATUSES = {"draft", "pending_review", "published", "rejected", "hidden"}
COMPOSER_ALLOWED_PUBLISH_TRANSITIONS = {
    ("draft", "published"),
    ("rejected", "published"),
    ("hidden", "published"),
}
COMPOSER_ALLOWED_REVIEW_TRANSITIONS = {
    ("draft", "pending_review"),
    ("rejected", "pending_review"),
}
MODERATOR_ALLOWED_TRANSITIONS = {
    ("pending_review", "published"),
    ("pending_review", "rejected"),
    ("published", "hidden"),
}
class CatalogAlbumUseCases:
    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    def create_album(
        self,
        actor_user_id: UUID,
        *,
        title: str,
        description: str | None,
        release_date: date | None,
    ) -> AlbumReadModel:
        normalized_title = _normalize_title(title)
        normalized_description = _normalize_optional_text(description)
        composer_profile_id = self._require_composer_profile(actor_user_id)
        return self._repository.create_album(
            owner_composer_id=composer_profile_id,
            title=normalized_title,
            description=normalized_description,
            release_date=release_date,
        )

    def update_album(
        self,
        actor_user_id: UUID,
        *,
        album_id: UUID,
        title: str,
        description: str | None,
        release_date: date | None,
    ) -> AlbumReadModel:
        normalized_title = _normalize_title(title)
        normalized_description = _normalize_optional_text(description)
        composer_profile_id = self._require_composer_profile(actor_user_id)
        album = self._require_owned_album(album_id, composer_profile_id)
        if album.status not in {"draft", "rejected", "hidden"}:
            raise ValidationError("Only draft, rejected or hidden albums can be edited.")
        updated = self._repository.update_album(
            album_id=album_id,
            title=normalized_title,
            description=normalized_description,
            release_date=release_date,
        )
        if updated is None:
            raise ValidationError("Album is not found.")
        return updated

    def replace_album_tracks(self, actor_user_id: UUID, *, album_id: UUID, track_ids: list[UUID]) -> AlbumReadModel:
        if not track_ids:
            raise ValidationError("Album should contain at least one track.")
        deduplicated_track_ids = list(dict.fromkeys(track_ids))
        composer_profile_id = self._require_composer_profile(actor_user_id)
        album = self._require_owned_album(album_id, composer_profile_id)
        if album.status not in {"draft", "rejected", "hidden"}:
            raise ValidationError("Tracks can be changed only for draft, rejected or hidden albums.")
        self._repository.replace_album_tracks(album_id, deduplicated_track_ids)
        refreshed = self._repository.get_album_by_id(album_id)
        if refreshed is None:
            raise ValidationError("Album is not found.")
        return refreshed

    def publish_album(self, actor_user_id: UUID, *, album_id: UUID) -> AlbumReadModel:
        composer_profile_id = self._require_composer_profile(actor_user_id)
        album = self._require_owned_album(album_id, composer_profile_id)
        if (album.status, "published") not in COMPOSER_ALLOWED_PUBLISH_TRANSITIONS:
            raise ValidationError("Composer cannot publish album from current status.")
        updated = self._repository.set_album_status(album_id, "published")
        if updated is None:
            raise ValidationError("Album is not found.")
        return updated

    def submit_album_for_review(self, actor_user_id: UUID, *, album_id: UUID) -> AlbumReadModel:
        composer_profile_id = self._require_composer_profile(actor_user_id)
        album = self._require_owned_album(album_id, composer_profile_id)
        if (album.status, "pending_review") not in COMPOSER_ALLOWED_REVIEW_TRANSITIONS:
            raise ValidationError("Album cannot be sent to review from current status.")
        updated = self._repository.set_album_status(album_id, "pending_review")
        if updated is None:
            raise ValidationError("Album is not found.")
        return updated

    def moderate_album(self, actor_roles: list[str], *, album_id: UUID, target_status: str) -> AlbumReadModel:
        normalized_status = target_status.strip().lower()
        if normalized_status not in ALBUM_STATUSES:
            raise ValidationError("Unsupported album status.")
        if not any(role in MODERATION_ROLES for role in actor_roles):
            raise AuthorizationError("Moderator or admin role is required.")
        album = self._repository.get_album_by_id(album_id)
        if album is None:
            raise ValidationError("Album is not found.")
        if (album.status, normalized_status) not in MODERATOR_ALLOWED_TRANSITIONS:
            raise ValidationError("Invalid moderation status transition.")
        updated = self._repository.set_album_status(album_id, normalized_status)
        if updated is None:
            raise ValidationError("Album is not found.")
        return updated

    def get_album(self, album_id: UUID, *, include_unpublished: bool) -> AlbumReadModel:
        album = self._repository.get_album_by_id(album_id)
        if album is None:
            raise ValidationError("Album is not found.")
        if not include_unpublished and album.status != "published":
            raise ValidationError("Album is not published.")
        return album

    def list_albums(
        self,
        *,
        status: str | None,
        owner_composer_id: UUID | None,
        include_unpublished: bool,
    ) -> list[AlbumReadModel]:
        normalized_status = status.strip().lower() if status else None
        if normalized_status is not None and normalized_status not in ALBUM_STATUSES:
            raise ValidationError("Unsupported album status filter.")
        filters = AlbumListFilter(
            status=normalized_status,
            owner_composer_id=owner_composer_id,
            include_unpublished=include_unpublished,
        )
        return self._repository.list_albums(filters)

    def _require_composer_profile(self, actor_user_id: UUID) -> UUID:
        roles = self._repository.get_user_role_codes(actor_user_id)
        composer_profile_id = self._repository.get_composer_profile_id_by_user_id(actor_user_id)
        return ensure_composer_access(actor_user_id, actor_roles=roles, composer_profile_id=composer_profile_id)

    def _require_owned_album(self, album_id: UUID, composer_profile_id: UUID) -> AlbumReadModel:
        album = self._repository.get_album_by_id(album_id)
        if album is None:
            raise ValidationError("Album is not found.")
        if album.owner_composer_id != composer_profile_id:
            raise AuthorizationError("Album is not owned by current composer.")
        return album


def _normalize_title(title: str) -> str:
    normalized = title.strip()
    if len(normalized) < 1 or len(normalized) > 255:
        raise ValidationError("Title length should be between 1 and 255 characters.")
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 4000:
        raise ValidationError("Description should contain at most 4000 characters.")
    return normalized
