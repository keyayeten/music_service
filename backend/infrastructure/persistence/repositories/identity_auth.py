from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.identity.repositories import (
    ComposerProfileReadModel,
    IdentityAuthRepository,
    IdentityUserAuthModel,
    IdentityUserReadModel,
)
from backend.infrastructure.persistence.models.identity import ComposerProfile, Role, User, UserRole, UserRoleProfile
from backend.infrastructure.persistence.seeds.identity_roles import seed_identity_roles


class SqlAlchemyIdentityAuthRepository(IdentityAuthRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_by_id(self, user_id: UUID) -> IdentityUserReadModel | None:
        user = await self._session.get(User, user_id)
        return _to_read_model(user) if user else None

    async def get_user_auth_by_login(self, login: str) -> IdentityUserAuthModel | None:
        query = select(User).where(or_(User.username == login, User.email == login))
        user = (await self._session.execute(query)).scalar_one_or_none()
        if user is None:
            return None
        return IdentityUserAuthModel(
            id=user.id,
            email=user.email,
            username=user.username,
            password_hash=user.password_hash,
            status=user.status,
        )

    async def create_user(self, email: str, username: str, password_hash: str, status: str = "active") -> IdentityUserReadModel:
        user = User(email=email, username=username, password_hash=password_hash, status=status)
        self._session.add(user)
        await self._session.flush()
        return _to_read_model(user)

    async def get_user_by_email(self, email: str) -> IdentityUserReadModel | None:
        user = (await self._session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        return _to_read_model(user) if user else None

    async def get_user_by_username(self, username: str) -> IdentityUserReadModel | None:
        user = (await self._session.execute(select(User).where(User.username == username))).scalar_one_or_none()
        return _to_read_model(user) if user else None

    async def ensure_roles_seeded(self) -> None:
        await self._session.run_sync(seed_identity_roles)
        await self._session.flush()

    async def get_role_id_by_code(self, code: str) -> int | None:
        return (await self._session.execute(select(Role.id).where(Role.code == code))).scalar_one_or_none()

    async def assign_role(self, user_id: UUID, role_id: int) -> None:
        user_role = await self._session.get(UserRole, {"user_id": user_id, "role_id": role_id})
        if user_role is None:
            self._session.add(UserRole(user_id=user_id, role_id=role_id))
            await self._session.flush()

    async def get_user_role_codes(self, user_id: UUID) -> list[str]:
        query = (
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.code.asc())
        )
        return list((await self._session.execute(query)).scalars())

    async def get_composer_profile_by_user_id(self, user_id: UUID) -> ComposerProfileReadModel | None:
        profile = (await self._session.execute(select(ComposerProfile).where(ComposerProfile.user_id == user_id))).scalar_one_or_none()
        return _to_composer_profile_read_model(profile) if profile else None

    async def upsert_composer_profile(
        self,
        *,
        user_id: UUID,
        display_name: str,
        bio: str | None,
        country_code: str | None,
    ) -> ComposerProfileReadModel:
        profile = (await self._session.execute(select(ComposerProfile).where(ComposerProfile.user_id == user_id))).scalar_one_or_none()
        if profile is None:
            profile = ComposerProfile(
                user_id=user_id,
                display_name=display_name,
                bio=bio,
                country_code=country_code,
                verified=False,
            )
            self._session.add(profile)
            await self._session.flush()
            return _to_composer_profile_read_model(profile)

        profile.display_name = display_name
        profile.bio = bio
        profile.country_code = country_code
        await self._session.flush()
        return _to_composer_profile_read_model(profile)

    async def upsert_user_role_profile(
        self,
        *,
        user_id: UUID,
        role_id: int,
        profile_type: str,
        profile_id: UUID,
    ) -> None:
        role_profile = (await self._session.execute(
            select(UserRoleProfile).where(
                UserRoleProfile.user_id == user_id,
                UserRoleProfile.role_id == role_id,
                UserRoleProfile.profile_type == profile_type,
            )
        )).scalar_one_or_none()
        if role_profile is None:
            self._session.add(
                UserRoleProfile(
                    user_id=user_id,
                    role_id=role_id,
                    profile_type=profile_type,
                    profile_id=profile_id,
                )
            )
            await self._session.flush()
            return

        role_profile.profile_id = profile_id
        await self._session.flush()


def _to_read_model(user: User) -> IdentityUserReadModel:
    return IdentityUserReadModel(
        id=user.id,
        email=user.email,
        username=user.username,
        status=user.status,
    )


def _to_composer_profile_read_model(profile: ComposerProfile) -> ComposerProfileReadModel:
    return ComposerProfileReadModel(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        bio=profile.bio,
        country_code=profile.country_code,
        verified=profile.verified,
    )
