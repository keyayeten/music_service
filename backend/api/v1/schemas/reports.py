from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateReportRequest(BaseModel):
    target_type: str
    target_id: str
    reason: str = Field(min_length=3, max_length=4000)


class UpdateReportStatusRequest(BaseModel):
    status: str


class ReportResponse(BaseModel):
    id: str
    reporter_user_id: str
    target_type: str
    target_id: str
    reason: str
    status: str
    created_at: datetime
    updated_at: datetime


class ListReportsResponse(BaseModel):
    items: list[ReportResponse]
