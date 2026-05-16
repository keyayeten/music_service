from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.domain.moderation.repositories import (
    ModerationActionReadModel,
    ModerationRepository,
    ReportListFilter,
    ReportReadModel,
)
from backend.infrastructure.persistence.models.identity import Role, UserRole
from backend.infrastructure.persistence.models.moderation import ModerationAction, Report


class SqlAlchemyModerationRepository(ModerationRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_report(
        self,
        *,
        reporter_user_id: UUID,
        target_type: str,
        target_id: UUID,
        reason: str,
    ) -> ReportReadModel:
        report = Report(
            reporter_user_id=reporter_user_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            status="open",
        )
        self._session.add(report)
        self._session.flush()
        return _to_report_read_model(report)

    def list_reports(self, filters: ReportListFilter) -> list[ReportReadModel]:
        query = select(Report).order_by(desc(Report.created_at))
        if filters.status is not None:
            query = query.where(Report.status == filters.status)
        if filters.target_type is not None:
            query = query.where(Report.target_type == filters.target_type)
        rows = self._session.execute(query).scalars()
        return [_to_report_read_model(row) for row in rows]

    def get_report_by_id(self, report_id: UUID) -> ReportReadModel | None:
        report = self._session.get(Report, report_id)
        if report is None:
            return None
        return _to_report_read_model(report)

    def set_report_status(self, report_id: UUID, status: str) -> ReportReadModel | None:
        report = self._session.get(Report, report_id)
        if report is None:
            return None
        report.status = status
        self._session.flush()
        return _to_report_read_model(report)

    def create_moderation_action(
        self,
        *,
        actor_user_id: UUID,
        target_type: str,
        target_id: UUID,
        action: str,
        metadata: dict | None,
    ) -> ModerationActionReadModel:
        moderation_action = ModerationAction(
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            meta=metadata,
        )
        self._session.add(moderation_action)
        self._session.flush()
        return _to_moderation_action_read_model(moderation_action)

    def list_moderation_actions_by_target(
        self,
        *,
        target_type: str,
        target_id: UUID,
    ) -> list[ModerationActionReadModel]:
        rows = self._session.execute(
            select(ModerationAction)
            .where(
                ModerationAction.target_type == target_type,
                ModerationAction.target_id == target_id,
            )
            .order_by(desc(ModerationAction.created_at))
        ).scalars()
        return [_to_moderation_action_read_model(row) for row in rows]

    def has_role(self, user_id: UUID, role_code: str) -> bool:
        row = self._session.execute(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Role.code == role_code)
        ).scalar_one_or_none()
        return row is not None


def _to_report_read_model(report: Report) -> ReportReadModel:
    return ReportReadModel(
        id=report.id,
        reporter_user_id=report.reporter_user_id,
        target_type=report.target_type,
        target_id=report.target_id,
        reason=report.reason,
        status=report.status,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def _to_moderation_action_read_model(action: ModerationAction) -> ModerationActionReadModel:
    return ModerationActionReadModel(
        id=action.id,
        actor_user_id=action.actor_user_id,
        target_type=action.target_type,
        target_id=action.target_id,
        action=action.action,
        metadata=action.meta,
        created_at=action.created_at,
    )
