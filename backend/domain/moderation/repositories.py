from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class ReportReadModel:
    id: UUID
    reporter_user_id: UUID
    target_type: str
    target_id: UUID
    reason: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ModerationActionReadModel:
    id: UUID
    actor_user_id: UUID
    target_type: str
    target_id: UUID
    action: str
    metadata: dict | None
    created_at: datetime


@dataclass(frozen=True)
class ReportListFilter:
    status: str | None = None
    target_type: str | None = None


class ModerationRepository(Protocol):
    async def create_report(
        self,
        *,
        reporter_user_id: UUID,
        target_type: str,
        target_id: UUID,
        reason: str,
    ) -> ReportReadModel:
        """Create a report in open status."""

    async def list_reports(self, filters: ReportListFilter) -> list[ReportReadModel]:
        """List reports with optional filters."""

    async def get_report_by_id(self, report_id: UUID) -> ReportReadModel | None:
        """Fetch report by id."""

    async def set_report_status(self, report_id: UUID, status: str) -> ReportReadModel | None:
        """Update report status."""

    async def create_moderation_action(
        self,
        *,
        actor_user_id: UUID,
        target_type: str,
        target_id: UUID,
        action: str,
        metadata: dict | None,
    ) -> ModerationActionReadModel:
        """Persist moderation action audit record."""

    async def list_moderation_actions_by_target(
        self,
        *,
        target_type: str,
        target_id: UUID,
    ) -> list[ModerationActionReadModel]:
        """List moderation audit records by target."""

    async def has_role(self, user_id: UUID, role_code: str) -> bool:
        """Check if user has role."""
