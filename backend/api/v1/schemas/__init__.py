from backend.api.v1.schemas.auth import (
    AuthSuccessResponse,
    ErrorResponse,
    LoginRequest,
    RefreshTokenRequest,
    SignupRequest,
    UserProfileResponse,
)
from backend.api.v1.schemas.catalog import (
    AlbumResponse,
    CreateAlbumRequest,
    CreateTrackRequest,
    ListAlbumsResponse,
    ListTracksResponse,
    ModerateAlbumRequest,
    ModerateTrackRequest,
    ReplaceAlbumTracksRequest,
    ReplaceTrackAuthorsRequest,
    TrackResponse,
    UpdateAlbumRequest,
    UpdateTrackRequest,
)
from backend.api.v1.schemas.profiles import ComposerProfileResponse, MyProfileResponse, UpdateMyProfileRequest

__all__ = [
    "SignupRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "UserProfileResponse",
    "AuthSuccessResponse",
    "ErrorResponse",
    "ComposerProfileResponse",
    "MyProfileResponse",
    "UpdateMyProfileRequest",
    "TrackResponse",
    "AlbumResponse",
    "ListTracksResponse",
    "ListAlbumsResponse",
    "CreateTrackRequest",
    "UpdateTrackRequest",
    "ReplaceTrackAuthorsRequest",
    "ModerateTrackRequest",
    "CreateAlbumRequest",
    "UpdateAlbumRequest",
    "ReplaceAlbumTracksRequest",
    "ModerateAlbumRequest",
]
"""Pydantic schemas for v1 HTTP contracts."""
