from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from backend.domain.catalog.repositories import CatalogRepository, TrackAuthorReadModel, TrackListFilter, TrackReadModel
from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.application.security.permissions import MODERATION_ROLES, ensure_composer_access

TRACK_STATUSES = {"draft", "pending_review", "published", "rejected", "hidden"}
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
class CatalogTrackUseCases:
    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    def create_track(self, actor_user_id: UUID, *, title: str, description: str | None, duration_seconds: int) -> TrackReadModel:
        normalized_title = _normalize_title(title)
        normalized_description = _normalize_optional_text(description)
        _validate_duration(duration_seconds)
        composer_profile_id = self._require_composer_profile(actor_user_id)
        return self._repository.create_track(
            title=normalized_title,
            description=normalized_description,
            duration_seconds=duration_seconds,
            primary_author_id=composer_profile_id,
        )

    def update_track(
        self,
        actor_user_id: UUID,
        *,
        track_id: UUID,
        title: str,
        description: str | None,
        duration_seconds: int,
    ) -> TrackReadModel:
        normalized_title = _normalize_title(title)
        normalized_description = _normalize_optional_text(description)
        _validate_duration(duration_seconds)
        composer_profile_id = self._require_composer_profile(actor_user_id)
        track = self._require_owned_track(track_id, composer_profile_id)
        if track.status not in {"draft", "rejected", "hidden"}:
            raise ValidationError("Only draft, rejected or hidden tracks can be edited.")
        updated = self._repository.update_track(
            track_id=track_id,
            title=normalized_title,
            description=normalized_description,
            duration_seconds=duration_seconds,
        )
        if updated is None:
            raise ValidationError("Track is not found.")
        return updated

    def set_track_authors(self, actor_user_id: UUID, *, track_id: UUID, author_profile_ids: list[UUID]) -> TrackReadModel:
        composer_profile_id = self._require_composer_profile(actor_user_id)
        track = self._require_owned_track(track_id, composer_profile_id)
        if track.status not in {"draft", "rejected", "hidden"}:
            raise ValidationError("Authors can be changed only for draft, rejected or hidden tracks.")
        if not author_profile_ids:
            raise ValidationError("Track should have at least one author.")
        unique_author_ids = list(dict.fromkeys(author_profile_ids))
        if composer_profile_id not in unique_author_ids:
            raise ValidationError("Current composer should be included in track authors.")
        authors = [
            TrackAuthorReadModel(
                composer_profile_id=author_id,
                contribution_role="composer",
                position=index + 1,
            )
            for index, author_id in enumerate(unique_author_ids)
        ]
        self._repository.replace_track_authors(track_id, authors)
        refreshed = self._repository.get_track_by_id(track_id)
        if refreshed is None:
            raise ValidationError("Track is not found.")
        return refreshed

    def publish_track(self, actor_user_id: UUID, *, track_id: UUID) -> TrackReadModel:
        composer_profile_id = self._require_composer_profile(actor_user_id)
        track = self._require_owned_track(track_id, composer_profile_id)
        if (track.status, "published") not in COMPOSER_ALLOWED_PUBLISH_TRANSITIONS:
            raise ValidationError("Composer cannot publish track from current status.")
        updated = self._repository.set_track_status(track_id, "published", datetime.now(UTC))
        if updated is None:
            raise ValidationError("Track is not found.")
        return updated

    def submit_track_for_review(self, actor_user_id: UUID, *, track_id: UUID) -> TrackReadModel:
        composer_profile_id = self._require_composer_profile(actor_user_id)
        track = self._require_owned_track(track_id, composer_profile_id)
        if (track.status, "pending_review") not in COMPOSER_ALLOWED_REVIEW_TRANSITIONS:
            raise ValidationError("Track cannot be sent to review from current status.")
        updated = self._repository.set_track_status(track_id, "pending_review", None)
        if updated is None:
            raise ValidationError("Track is not found.")
        return updated

    def moderate_track(self, actor_roles: list[str], *, track_id: UUID, target_status: str) -> TrackReadModel:
        normalized_status = target_status.strip().lower()
        if normalized_status not in TRACK_STATUSES:
            raise ValidationError("Unsupported track status.")
        if not any(role in MODERATION_ROLES for role in actor_roles):
            raise AuthorizationError("Moderator or admin role is required.")
        track = self._repository.get_track_by_id(track_id)
        if track is None:
            raise ValidationError("Track is not found.")
        if (track.status, normalized_status) not in MODERATOR_ALLOWED_TRANSITIONS:
            raise ValidationError("Invalid moderation status transition.")
        published_at = track.published_at
        if normalized_status == "published":
            published_at = datetime.now(UTC)
        if normalized_status in {"rejected", "hidden"}:
            published_at = None
        updated = self._repository.set_track_status(track_id, normalized_status, published_at)
        if updated is None:
            raise ValidationError("Track is not found.")
        return updated

    def get_track(self, track_id: UUID, *, include_unpublished: bool) -> TrackReadModel:
        track = self._repository.get_track_by_id(track_id)
        if track is None:
            raise ValidationError("Track is not found.")
        if not include_unpublished and track.status != "published":
            raise ValidationError("Track is not published.")
        return track

    def list_tracks(
        self,
        *,
        status: str | None,
        genre_code: str | None,
        author_id: UUID | None,
        include_unpublished: bool,
    ) -> list[TrackReadModel]:
        normalized_status = status.strip().lower() if status else None
        if normalized_status is not None and normalized_status not in TRACK_STATUSES:
            raise ValidationError("Unsupported track status filter.")
        filters = TrackListFilter(
            status=normalized_status,
            genre_code=genre_code.strip().lower() if genre_code else None,
            author_id=author_id,
            include_unpublished=include_unpublished,
        )
        return self._repository.list_tracks(filters)

    def _require_composer_profile(self, actor_user_id: UUID) -> UUID:
        roles = self._repository.get_user_role_codes(actor_user_id)
        composer_profile_id = self._repository.get_composer_profile_id_by_user_id(actor_user_id)
        return ensure_composer_access(actor_user_id, actor_roles=roles, composer_profile_id=composer_profile_id)

    def _require_owned_track(self, track_id: UUID, composer_profile_id: UUID) -> TrackReadModel:
        track = self._repository.get_track_by_id(track_id)
        if track is None:
            raise ValidationError("Track is not found.")
        if composer_profile_id not in {author.composer_profile_id for author in track.authors}:
            raise AuthorizationError("Track is not owned by current composer.")
        return track


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


def _validate_duration(duration_seconds: int) -> None:
    if duration_seconds <= 0:
        raise ValidationError("Duration should be a positive number.")
