from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from backend.application.security.permissions import MODERATION_ROLES, USER_ROLE, ensure_any_role
from backend.domain.common.exceptions import ValidationError
from backend.domain.moderation.repositories import ModerationRepository, ReportListFilter, ReportReadModel

REPORT_TARGET_TYPES = {"track", "album", "playlist", "comment"}
REPORT_STATUSES = {"open", "in_review", "resolved", "rejected"}
REPORT_STATUS_TRANSITIONS = {
    ("open", "in_review"),
    ("in_review", "resolved"),
    ("in_review", "rejected"),
}


@dataclass(frozen=True)
class ReportStatusUpdateResult:
    report: ReportReadModel
    audit_action_id: UUID


class ModerationReportUseCases:
    def __init__(self, repository: ModerationRepository) -> None:
        self._repository = repository

    def create_report(self, actor_user_id: UUID, *, target_type: str, target_id: UUID, reason: str) -> ReportReadModel:
        ensure_any_role(
            self._resolve_roles(actor_user_id),
            allowed_roles={USER_ROLE, "composer", "moderator", "admin"},
            message="User role is required to create reports.",
        )
        normalized_target_type = _normalize_target_type(target_type)
        normalized_reason = _normalize_reason(reason)
        return self._repository.create_report(
            reporter_user_id=actor_user_id,
            target_type=normalized_target_type,
            target_id=target_id,
            reason=normalized_reason,
        )

    def list_reports(self, actor_user_id: UUID, *, status: str | None, target_type: str | None) -> list[ReportReadModel]:
        ensure_any_role(
            self._resolve_roles(actor_user_id),
            allowed_roles=MODERATION_ROLES,
            message="Moderator or admin role is required.",
        )
        normalized_status = _normalize_status(status) if status is not None else None
        normalized_target_type = _normalize_target_type(target_type) if target_type is not None else None
        return self._repository.list_reports(ReportListFilter(status=normalized_status, target_type=normalized_target_type))

    def get_report(self, actor_user_id: UUID, *, report_id: UUID) -> ReportReadModel:
        ensure_any_role(
            self._resolve_roles(actor_user_id),
            allowed_roles=MODERATION_ROLES,
            message="Moderator or admin role is required.",
        )
        report = self._repository.get_report_by_id(report_id)
        if report is None:
            raise ValidationError("Report is not found.")
        return report

    def set_report_status(self, actor_user_id: UUID, *, report_id: UUID, target_status: str) -> ReportStatusUpdateResult:
        ensure_any_role(
            self._resolve_roles(actor_user_id),
            allowed_roles=MODERATION_ROLES,
            message="Moderator or admin role is required.",
        )
        normalized_target_status = _normalize_status(target_status)
        report = self._repository.get_report_by_id(report_id)
        if report is None:
            raise ValidationError("Report is not found.")
        if (report.status, normalized_target_status) not in REPORT_STATUS_TRANSITIONS:
            raise ValidationError("Invalid report status transition.")
        updated_report = self._repository.set_report_status(report_id, normalized_target_status)
        if updated_report is None:
            raise ValidationError("Report is not found.")
        action = self._repository.create_moderation_action(
            actor_user_id=actor_user_id,
            target_type="report",
            target_id=report_id,
            action="report_status_updated",
            metadata={
                "old_status": report.status,
                "new_status": normalized_target_status,
            },
        )
        return ReportStatusUpdateResult(report=updated_report, audit_action_id=action.id)

    def _resolve_roles(self, user_id: UUID) -> list[str]:
        return [
            role
            for role in ("admin", "moderator", "composer", "user")
            if self._repository.has_role(user_id, role)
        ]


def _normalize_target_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in REPORT_TARGET_TYPES:
        raise ValidationError("Unsupported report target type.")
    return normalized


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in REPORT_STATUSES:
        raise ValidationError("Unsupported report status.")
    return normalized


def _normalize_reason(reason: str) -> str:
    normalized = reason.strip()
    if len(normalized) < 3 or len(normalized) > 4000:
        raise ValidationError("Reason length should be between 3 and 4000 characters.")
    return normalized
