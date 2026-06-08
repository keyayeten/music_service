from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class TrackAuthorResponse(BaseModel):
    composer_profile_id: str
    contribution_role: str
    position: int


class TrackResponse(BaseModel):
    id: str
    title: str
    description: str | None
    status: str
    duration_seconds: int
    plays_count: int
    likes_count: int
    comments_count: int
    published_at: datetime | None
    created_at: datetime
    authors: list[TrackAuthorResponse]
    genre_codes: list[str]


class AlbumTrackResponse(BaseModel):
    track_id: str
    position: int


class AlbumResponse(BaseModel):
    id: str
    owner_composer_id: str
    title: str
    description: str | None
    status: str
    release_date: date | None
    likes_count: int
    comments_count: int
    created_at: datetime
    track_items: list[AlbumTrackResponse]


class CreateTrackRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    duration_seconds: int = Field(gt=0)


class UpdateTrackRequest(CreateTrackRequest):
    pass


class ReplaceTrackAuthorsRequest(BaseModel):
    author_profile_ids: list[str] = Field(min_length=1)


class ModerateTrackRequest(BaseModel):
    target_status: str = Field(min_length=3, max_length=32)


class ListTracksResponse(BaseModel):
    items: list[TrackResponse]


class CreateAlbumRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    release_date: date | None = None


class UpdateAlbumRequest(CreateAlbumRequest):
    pass


class ReplaceAlbumTracksRequest(BaseModel):
    track_ids: list[str] = Field(min_length=1)


class ModerateAlbumRequest(BaseModel):
    target_status: str = Field(min_length=3, max_length=32)


class ListAlbumsResponse(BaseModel):
    items: list[AlbumResponse]
