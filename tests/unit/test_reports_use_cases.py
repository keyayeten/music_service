from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from backend.application.moderation.use_cases.reports import ModerationReportUseCases
from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.domain.moderation.repositories import ModerationActionReadModel, ReportListFilter, ReportReadModel


class _FakeModerationRepository:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.moderator_user_id = uuid4()
        self._roles = {
            self.user_id: {"user"},
            self.moderator_user_id: {"moderator"},
        }
        self.report = ReportReadModel(
            id=uuid4(),
            reporter_user_id=self.user_id,
            target_type="track",
            target_id=uuid4(),
            reason="Spam",
            status="open",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.last_action: ModerationActionReadModel | None = None

    def create_report(self, *, reporter_user_id: UUID, target_type: str, target_id: UUID, reason: str) -> ReportReadModel:
        now = datetime.now(UTC)
        self.report = ReportReadModel(
            id=uuid4(),
            reporter_user_id=reporter_user_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            status="open",
            created_at=now,
            updated_at=now,
        )
        return self.report

    def list_reports(self, filters: ReportListFilter) -> list[ReportReadModel]:
        if filters.status is not None and self.report.status != filters.status:
            return []
        if filters.target_type is not None and self.report.target_type != filters.target_type:
            return []
        return [self.report]

    def get_report_by_id(self, report_id: UUID) -> ReportReadModel | None:
        if report_id == self.report.id:
            return self.report
        return None

    def set_report_status(self, report_id: UUID, status: str) -> ReportReadModel | None:
        if report_id != self.report.id:
            return None
        self.report = ReportReadModel(
            id=self.report.id,
            reporter_user_id=self.report.reporter_user_id,
            target_type=self.report.target_type,
            target_id=self.report.target_id,
            reason=self.report.reason,
            status=status,
            created_at=self.report.created_at,
            updated_at=datetime.now(UTC),
        )
        return self.report

    def create_moderation_action(
        self,
        *,
        actor_user_id: UUID,
        target_type: str,
        target_id: UUID,
        action: str,
        metadata: dict | None,
    ) -> ModerationActionReadModel:
        self.last_action = ModerationActionReadModel(
            id=uuid4(),
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
            metadata=metadata,
            created_at=datetime.now(UTC),
        )
        return self.last_action

    def list_moderation_actions_by_target(self, *, target_type: str, target_id: UUID) -> list[ModerationActionReadModel]:
        if self.last_action is None:
            return []
        if self.last_action.target_type != target_type or self.last_action.target_id != target_id:
            return []
        return [self.last_action]

    def has_role(self, user_id: UUID, role_code: str) -> bool:
        return role_code in self._roles.get(user_id, set())


@pytest.mark.unit
def test_create_report_requires_user_role() -> None:
    repository = _FakeModerationRepository()
    use_cases = ModerationReportUseCases(repository)
    outsider_user_id = uuid4()

    with pytest.raises(AuthorizationError):
        use_cases.create_report(outsider_user_id, target_type="track", target_id=uuid4(), reason="Spam content")


@pytest.mark.unit
def test_set_report_status_writes_audit_action() -> None:
    repository = _FakeModerationRepository()
    use_cases = ModerationReportUseCases(repository)

    use_cases.set_report_status(repository.moderator_user_id, report_id=repository.report.id, target_status="in_review")

    assert repository.last_action is not None
    assert repository.last_action.target_type == "report"
    assert repository.last_action.action == "report_status_updated"


@pytest.mark.unit
def test_set_report_status_rejects_invalid_transition() -> None:
    repository = _FakeModerationRepository()
    use_cases = ModerationReportUseCases(repository)

    with pytest.raises(ValidationError):
        use_cases.set_report_status(repository.moderator_user_id, report_id=repository.report.id, target_status="resolved")
