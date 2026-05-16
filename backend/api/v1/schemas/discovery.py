from __future__ import annotations

from pydantic import BaseModel, Field


class ExternalLinkClickResponse(BaseModel):
    status: str
    external_link_id: str


class RecommendedTrackItem(BaseModel):
    track_id: str
    score: float
    source: str


class ListRecommendedTracksResponse(BaseModel):
    items: list[RecommendedTrackItem]


class RecommendationQueryParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
