from __future__ import annotations

from pydantic import BaseModel, Field


class ComposerProfileResponse(BaseModel):
    id: str
    display_name: str
    bio: str | None
    country_code: str | None
    verified: bool


class MyProfileResponse(BaseModel):
    id: str
    email: str
    username: str
    status: str
    roles: list[str]
    composer_profile: ComposerProfileResponse | None


class UpdateMyProfileRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
