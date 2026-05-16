from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from starlette.requests import Request
from wtforms import PasswordField

from backend.application.identity.security import hash_password
from backend.infrastructure.admin.auth import get_session_user_id
from backend.infrastructure.persistence.models.identity import ComposerProfile, Role, User, UserRole, UserRoleProfile


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    category = "Identity"
    column_list = [User.id, User.email, User.username, User.status, User.is_superuser, User.created_at]
    column_searchable_list = [User.email, User.username]
    column_sortable_list = [User.email, User.username, User.status, User.is_superuser, User.created_at]
    column_details_exclude_list = [User.password_hash]
    form_excluded_columns = [User.password_hash, User.created_at, User.updated_at]
    form_extra_fields = {"password": PasswordField("Password")}
    form_create_rules = ["email", "username", "password", "status", "is_superuser"]
    form_edit_rules = ["email", "username", "password", "status", "is_superuser"]

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: User,
        is_created: bool,
        request: Request,
    ) -> None:
        password = data.pop("password", None)
        if password:
            model.password_hash = hash_password(str(password))
        elif is_created:
            raise ValueError("Password is required when creating a user.")

        if data.get("is_superuser") and not model.is_superuser:
            if get_session_user_id(request) is None:
                raise ValueError("Only authenticated superusers can grant superuser access.")


class RoleAdmin(ModelView, model=Role):
    name = "Role"
    name_plural = "Roles"
    category = "Identity"
    column_list = [Role.id, Role.code, Role.name]
    column_searchable_list = [Role.code, Role.name]


class UserRoleAdmin(ModelView, model=UserRole):
    name = "User role"
    name_plural = "User roles"
    category = "Identity"
    column_list = [UserRole.user_id, UserRole.role_id, UserRole.assigned_at]


class ComposerProfileAdmin(ModelView, model=ComposerProfile):
    name = "Composer profile"
    name_plural = "Composer profiles"
    category = "Identity"
    column_list = [
        ComposerProfile.id,
        ComposerProfile.user_id,
        ComposerProfile.display_name,
        ComposerProfile.verified,
        ComposerProfile.created_at,
    ]
    column_searchable_list = [ComposerProfile.display_name]


class UserRoleProfileAdmin(ModelView, model=UserRoleProfile):
    name = "User role profile"
    name_plural = "User role profiles"
    category = "Identity"
    column_list = [
        UserRoleProfile.id,
        UserRoleProfile.user_id,
        UserRoleProfile.role_id,
        UserRoleProfile.profile_type,
        UserRoleProfile.profile_id,
    ]
