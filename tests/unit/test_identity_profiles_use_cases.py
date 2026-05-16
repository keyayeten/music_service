from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from backend.application.identity.use_cases.profiles import COMPOSER_PROFILE_TYPE, IdentityProfilesUseCases
from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.domain.identity.repositories import ComposerProfileReadModel, IdentityUserReadModel
from tests.async_tools import run_async


class _FakeIdentityRepository:
    def __init__(self) -> None:
        self.user = IdentityUserReadModel(
            id=uuid4(),
            email="user@example.com",
            username="stage2_user",
            status="active",
        )
        self.role_codes = ["user", "composer"]
        self.role_id_by_code = {"composer": 3}
        self.composer_profile: ComposerProfileReadModel | None = None
        self.linked_profile: tuple[UUID, int, str, UUID] | None = None

    async def get_user_by_id(self, user_id: UUID) -> IdentityUserReadModel | None:
        return self.user if user_id == self.user.id else None

    async def get_user_role_codes(self, user_id: UUID) -> list[str]:
        if user_id != self.user.id:
            return []
        return list(self.role_codes)

    async def get_role_id_by_code(self, code: str) -> int | None:
        return self.role_id_by_code.get(code)

    async def get_composer_profile_by_user_id(self, user_id: UUID) -> ComposerProfileReadModel | None:
        if user_id != self.user.id:
            return None
        return self.composer_profile

    async def upsert_composer_profile(
        self,
        *,
        user_id: UUID,
        display_name: str,
        bio: str | None,
        country_code: str | None,
    ) -> ComposerProfileReadModel:
        if self.composer_profile is None:
            self.composer_profile = ComposerProfileReadModel(
                id=uuid4(),
                user_id=user_id,
                display_name=display_name,
                bio=bio,
                country_code=country_code,
                verified=False,
            )
            return self.composer_profile
        self.composer_profile = replace(
            self.composer_profile,
            display_name=display_name,
            bio=bio,
            country_code=country_code,
        )
        return self.composer_profile

    async def upsert_user_role_profile(
        self,
        *,
        user_id: UUID,
        role_id: int,
        profile_type: str,
        profile_id: UUID,
    ) -> None:
        self.linked_profile = (user_id, role_id, profile_type, profile_id)


@pytest.mark.unit
def test_update_profile_requires_composer_role() -> None:
    repository = _FakeIdentityRepository()
    repository.role_codes = ["user"]
    use_cases = IdentityProfilesUseCases(repository=repository)

    with pytest.raises(AuthorizationError):
        run_async(
            use_cases.update_my_profile(
                repository.user.id,
                display_name="Composer",
                bio="Bio",
                country_code="US",
            )
        )


@pytest.mark.unit
def test_update_profile_links_role_profile() -> None:
    repository = _FakeIdentityRepository()
    use_cases = IdentityProfilesUseCases(repository=repository)

    result = run_async(
        use_cases.update_my_profile(
            repository.user.id,
            display_name="Composer Name",
            bio="Short bio",
            country_code="us",
        )
    )

    assert result.composer_profile is not None
    assert result.composer_profile.country_code == "US"
    assert repository.linked_profile is not None
    assert repository.linked_profile[2] == COMPOSER_PROFILE_TYPE
    assert repository.linked_profile[3] == result.composer_profile.id


@pytest.mark.unit
def test_update_profile_validates_country_code() -> None:
    repository = _FakeIdentityRepository()
    use_cases = IdentityProfilesUseCases(repository=repository)

    with pytest.raises(ValidationError):
        run_async(
            use_cases.update_my_profile(
                repository.user.id,
                display_name="Composer Name",
                bio="Bio",
                country_code="USA",
            )
        )
