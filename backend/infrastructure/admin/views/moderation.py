from sqladmin import ModelView

from backend.infrastructure.persistence.models.moderation import ModerationAction, Report


class ReportAdmin(ModelView, model=Report):
    name = "Report"
    name_plural = "Reports"
    category = "Moderation"
    column_list = [Report.id, Report.reporter_user_id, Report.target_type, Report.target_id, Report.status, Report.created_at]
    column_sortable_list = [Report.status, Report.created_at]
    form_excluded_columns = [Report.created_at, Report.updated_at]


class ModerationActionAdmin(ModelView, model=ModerationAction):
    name = "Moderation action"
    name_plural = "Moderation actions"
    category = "Moderation"
    column_list = [
        ModerationAction.id,
        ModerationAction.actor_user_id,
        ModerationAction.target_type,
        ModerationAction.target_id,
        ModerationAction.action,
        ModerationAction.created_at,
    ]
    column_sortable_list = [ModerationAction.created_at, ModerationAction.action]
    can_create = False
    can_edit = False
    can_delete = False
