from __future__ import annotations

from dataclasses import dataclass
import logging
from uuid import UUID

from backend.application.identity.security import decode_jwt, hash_password, issue_token_pair, verify_password
from backend.domain.common.exceptions import AuthenticationError, ConflictError, ValidationError
from backend.domain.identity.repositories import IdentityAuthRepository, IdentityUserReadModel

logger = logging.getLogger("backend.auth")


@dataclass(frozen=True)
class AuthResult:
    user: IdentityUserReadModel
    access_token: str
    refresh_token: str
    token_type: str
    access_expires_in: int
    refresh_expires_in: int


class IdentityAuthUseCases:
    def __init__(
        self,
        repository: IdentityAuthRepository,
        jwt_secret: str,
        jwt_access_ttl_minutes: int,
        jwt_refresh_ttl_minutes: int,
    ) -> None:
        self._repository = repository
        self._jwt_secret = jwt_secret
        self._jwt_access_ttl_minutes = jwt_access_ttl_minutes
        self._jwt_refresh_ttl_minutes = jwt_refresh_ttl_minutes

    async def signup(self, email: str, username: str, password: str) -> AuthResult:
        normalized_email = email.strip().lower()
        normalized_username = username.strip()
        logger.info("Signup attempt username=%s email=%s", normalized_username, _mask_email(normalized_email))
        self._validate_signup_fields(normalized_email, normalized_username, password)

        if await self._repository.get_user_by_email(normalized_email):
            logger.info("Signup rejected: email already registered email=%s", _mask_email(normalized_email))
            raise ConflictError("Email is already registered.")
        if await self._repository.get_user_by_username(normalized_username):
            logger.info("Signup rejected: username already registered username=%s", normalized_username)
            raise ConflictError("Username is already registered.")

        password_hash = hash_password(password)
        await self._repository.ensure_roles_seeded()
        user = await self._repository.create_user(
            email=normalized_email,
            username=normalized_username,
            password_hash=password_hash,
        )
        role_id = await self._repository.get_role_id_by_code("user")
        if role_id is None:
            raise ValidationError("Default role is not configured.")
        await self._repository.assign_role(user.id, role_id)

        tokens = issue_token_pair(
            user.id,
            self._jwt_secret,
            self._jwt_access_ttl_minutes,
            self._jwt_refresh_ttl_minutes,
        )
        logger.info("Signup succeeded user_id=%s username=%s", user.id, user.username)
        return AuthResult(user=user, **tokens)

    async def login(self, login: str, password: str) -> AuthResult:
        if not login.strip() or not password:
            raise ValidationError("Login and password are required.")

        login_value = login.strip()
        logger.info("Login attempt login=%s", _mask_login(login_value))
        user_auth = await self._repository.get_user_auth_by_login(login_value)
        if user_auth is None or not verify_password(password, user_auth.password_hash):
            logger.info("Login failed: invalid credentials login=%s", _mask_login(login_value))
            raise AuthenticationError("Invalid username/email or password.")
        if user_auth.status != "active":
            logger.info("Login failed: inactive user user_id=%s", user_auth.id)
            raise AuthenticationError("User is not active.")

        user = await self._repository.get_user_by_id(user_auth.id)
        if user is None:
            raise AuthenticationError("User is not found.")

        tokens = issue_token_pair(
            user.id,
            self._jwt_secret,
            self._jwt_access_ttl_minutes,
            self._jwt_refresh_ttl_minutes,
        )
        logger.info("Login succeeded user_id=%s", user.id)
        return AuthResult(user=user, **tokens)

    async def refresh(self, refresh_token: str) -> AuthResult:
        logger.info("Refresh token attempt.")
        payload = decode_jwt(refresh_token, self._jwt_secret)
        token_type = payload.get("type")
        if token_type != "refresh":
            raise AuthenticationError("Token type is not refresh.")

        user_id_raw = payload.get("sub")
        if not isinstance(user_id_raw, str):
            raise AuthenticationError("Invalid token subject.")
        try:
            user_id = UUID(user_id_raw)
        except ValueError as exc:
            raise AuthenticationError("Invalid token subject.") from exc

        user = await self._repository.get_user_by_id(user_id)
        if user is None:
            raise AuthenticationError("User is not found.")
        if user.status != "active":
            raise AuthenticationError("User is not active.")

        tokens = issue_token_pair(
            user.id,
            self._jwt_secret,
            self._jwt_access_ttl_minutes,
            self._jwt_refresh_ttl_minutes,
        )
        logger.info("Refresh token succeeded user_id=%s", user.id)
        return AuthResult(user=user, **tokens)

    async def get_current_user(self, access_token: str) -> IdentityUserReadModel:
        payload = decode_jwt(access_token, self._jwt_secret)
        token_type = payload.get("type")
        if token_type != "access":
            raise AuthenticationError("Token type is not access.")
        user_id_raw = payload.get("sub")
        if not isinstance(user_id_raw, str):
            raise AuthenticationError("Invalid token subject.")

        try:
            user_id = UUID(user_id_raw)
        except ValueError as exc:
            raise AuthenticationError("Invalid token subject.") from exc

        user = await self._repository.get_user_by_id(user_id)
        if user is None:
            raise AuthenticationError("User is not found.")
        if user.status != "active":
            raise AuthenticationError("User is not active.")
        return user

    @staticmethod
    def _validate_signup_fields(email: str, username: str, password: str) -> None:
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValidationError("Email is invalid.")
        if len(username) < 3 or len(username) > 64:
            raise ValidationError("Username length should be between 3 and 64 characters.")
        if len(password) < 8:
            raise ValidationError("Password must contain at least 8 characters.")


def _mask_email(email: str) -> str:
    local_part, _, domain = email.partition("@")
    if not domain:
        return "***"
    if len(local_part) <= 2:
        return f"{local_part[0:1]}***@{domain}" if local_part else f"***@{domain}"
    return f"{local_part[:2]}***@{domain}"


def _mask_login(login: str) -> str:
    if "@" in login:
        return _mask_email(login)
    if len(login) <= 2:
        return f"{login[0:1]}***" if login else "***"
    return f"{login[:2]}***"
