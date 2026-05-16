from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from backend.application.identity.security import verify_password
from backend.infrastructure.persistence.database import get_session_factory
from backend.infrastructure.persistence.models.identity import User

_SESSION_USER_ID_KEY = "user_id"


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        login_value = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))
        if not login_value or not password:
            return False

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = (
                await session.execute(
                    select(User).where(or_(User.email == login_value, User.username == login_value))
                )
            ).scalar_one_or_none()
            if user is None or not user.is_superuser:
                return False
            if user.status != "active":
                return False
            if not verify_password(password, user.password_hash):
                return False
            request.session[_SESSION_USER_ID_KEY] = str(user.id)
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id_raw = request.session.get(_SESSION_USER_ID_KEY)
        if not isinstance(user_id_raw, str):
            return False
        try:
            user_id = UUID(user_id_raw)
        except ValueError:
            return False

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await session.get(User, user_id)
            if user is None or not user.is_superuser or user.status != "active":
                request.session.clear()
                return False
        return True


def get_session_user_id(request: Request) -> UUID | None:
    user_id_raw = request.session.get(_SESSION_USER_ID_KEY)
    if not isinstance(user_id_raw, str):
        return None
    try:
        return UUID(user_id_raw)
    except ValueError:
        return None
