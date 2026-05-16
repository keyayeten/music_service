from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from backend.application.identity.security import decode_jwt, hash_password, issue_token_pair, verify_password
from backend.domain.common.exceptions import AuthenticationError, ConflictError, ValidationError
from backend.domain.identity.repositories import IdentityAuthRepository, IdentityUserReadModel


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

    def signup(self, email: str, username: str, password: str) -> AuthResult:
        normalized_email = email.strip().lower()
        normalized_username = username.strip()
        self._validate_signup_fields(normalized_email, normalized_username, password)

        if self._repository.get_user_by_email(normalized_email):
            raise ConflictError("Email is already registered.")
        if self._repository.get_user_by_username(normalized_username):
            raise ConflictError("Username is already registered.")

        password_hash = hash_password(password)
        self._repository.ensure_roles_seeded()
        user = self._repository.create_user(
            email=normalized_email,
            username=normalized_username,
            password_hash=password_hash,
        )
        role_id = self._repository.get_role_id_by_code("user")
        if role_id is None:
            raise ValidationError("Default role is not configured.")
        self._repository.assign_role(user.id, role_id)

        tokens = issue_token_pair(
            user.id,
            self._jwt_secret,
            self._jwt_access_ttl_minutes,
            self._jwt_refresh_ttl_minutes,
        )
        return AuthResult(user=user, **tokens)

    def login(self, login: str, password: str) -> AuthResult:
        if not login.strip() or not password:
            raise ValidationError("Login and password are required.")

        user_auth = self._repository.get_user_auth_by_login(login.strip())
        if user_auth is None or not verify_password(password, user_auth.password_hash):
            raise AuthenticationError("Invalid username/email or password.")
        if user_auth.status != "active":
            raise AuthenticationError("User is not active.")

        user = self._repository.get_user_by_id(user_auth.id)
        if user is None:
            raise AuthenticationError("User is not found.")

        tokens = issue_token_pair(
            user.id,
            self._jwt_secret,
            self._jwt_access_ttl_minutes,
            self._jwt_refresh_ttl_minutes,
        )
        return AuthResult(user=user, **tokens)

    def refresh(self, refresh_token: str) -> AuthResult:
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

        user = self._repository.get_user_by_id(user_id)
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
        return AuthResult(user=user, **tokens)

    def get_current_user(self, access_token: str) -> IdentityUserReadModel:
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

        user = self._repository.get_user_by_id(user_id)
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
