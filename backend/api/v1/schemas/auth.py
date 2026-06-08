from __future__ import annotations

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=255, description="Username or email.")
    password: str = Field(min_length=8, max_length=256)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=16)


class UserProfileResponse(BaseModel):
    id: str
    email: str
    username: str
    status: str
    roles: list[str]


class AuthTokensResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_in: int
    refresh_expires_in: int


class AuthSuccessResponse(BaseModel):
    user: UserProfileResponse
    tokens: AuthTokensResponse


class ErrorResponse(BaseModel):
    code: str
    message: str
