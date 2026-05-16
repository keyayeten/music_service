from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.domain.identity.repositories import ComposerProfileReadModel, IdentityAuthRepository, IdentityUserReadModel

COMPOSER_PROFILE_TYPE = "composer_profile"
COMPOSER_ROLE_CODE = "composer"


@dataclass(frozen=True)
class IdentityProfileResult:
    user: IdentityUserReadModel
    roles: list[str]
    composer_profile: ComposerProfileReadModel | None


class IdentityProfilesUseCases:
    def __init__(self, repository: IdentityAuthRepository) -> None:
        self._repository = repository

    def get_my_profile(self, user_id: UUID) -> IdentityProfileResult:
        user = self._repository.get_user_by_id(user_id)
        if user is None:
            raise ValidationError("User is not found.")

        roles = self._repository.get_user_role_codes(user_id)
        composer_profile = self._repository.get_composer_profile_by_user_id(user_id)
        return IdentityProfileResult(user=user, roles=roles, composer_profile=composer_profile)

    def update_my_profile(
        self,
        user_id: UUID,
        *,
        display_name: str,
        bio: str | None,
        country_code: str | None,
    ) -> IdentityProfileResult:
        normalized_display_name = display_name.strip()
        normalized_bio = bio.strip() if bio is not None else None
        normalized_country_code = country_code.strip().upper() if country_code is not None else None

        self._validate_update_payload(normalized_display_name, normalized_bio, normalized_country_code)

        role_codes = self._repository.get_user_role_codes(user_id)
        if COMPOSER_ROLE_CODE not in role_codes:
            raise AuthorizationError("Composer role is required to manage composer profile.")

        role_id = self._repository.get_role_id_by_code(COMPOSER_ROLE_CODE)
        if role_id is None:
            raise ValidationError("Composer role is not configured.")

        composer_profile = self._repository.upsert_composer_profile(
            user_id=user_id,
            display_name=normalized_display_name,
            bio=normalized_bio,
            country_code=normalized_country_code,
        )
        self._repository.upsert_user_role_profile(
            user_id=user_id,
            role_id=role_id,
            profile_type=COMPOSER_PROFILE_TYPE,
            profile_id=composer_profile.id,
        )
        user = self._repository.get_user_by_id(user_id)
        if user is None:
            raise ValidationError("User is not found.")

        return IdentityProfileResult(user=user, roles=role_codes, composer_profile=composer_profile)

    @staticmethod
    def _validate_update_payload(display_name: str, bio: str | None, country_code: str | None) -> None:
        if len(display_name) < 2 or len(display_name) > 120:
            raise ValidationError("Display name length should be between 2 and 120 characters.")
        if bio is not None and len(bio) > 2000:
            raise ValidationError("Bio must contain at most 2000 characters.")
        if country_code is not None:
            if len(country_code) != 2 or not country_code.isalpha():
                raise ValidationError("Country code must be ISO alpha-2.")
