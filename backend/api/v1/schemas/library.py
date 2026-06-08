from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PlaylistTrackItemResponse(BaseModel):
    track_id: str
    added_by_user_id: str
    position: int
    added_at: datetime


class PlaylistResponse(BaseModel):
    id: str
    owner_user_id: str
    title: str
    description: str | None
    visibility: str
    likes_count: int
    comments_count: int
    created_at: datetime
    track_items: list[PlaylistTrackItemResponse]


class LibraryItemResponse(BaseModel):
    id: str
    user_id: str
    item_type: str
    item_id: str
    section: str
    created_at: datetime


class CreatePlaylistRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    visibility: str = Field(min_length=6, max_length=32)


class UpdatePlaylistRequest(CreatePlaylistRequest):
    pass


class AddPlaylistTrackRequest(BaseModel):
    track_id: str
    position: int | None = Field(default=None, gt=0)


class ReorderPlaylistTracksRequest(BaseModel):
    track_ids: list[str] = Field(min_length=1)


class AddLibraryItemRequest(BaseModel):
    item_type: str = Field(min_length=4, max_length=32)
    item_id: str
    section: str = Field(min_length=5, max_length=32)


class ListPlaylistsResponse(BaseModel):
    items: list[PlaylistResponse]


class ListLibraryItemsResponse(BaseModel):
    items: list[LibraryItemResponse]
