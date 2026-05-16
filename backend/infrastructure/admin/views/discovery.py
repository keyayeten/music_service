from sqladmin import ModelView

from backend.infrastructure.persistence.models.discovery import ExternalLinkClick, UserTrackEvent
class UserTrackEventAdmin(ModelView, model=UserTrackEvent):
    name = "User track event"
    name_plural = "User track events"
    category = "Discovery"
    column_list = [UserTrackEvent.id, UserTrackEvent.user_id, UserTrackEvent.track_id, UserTrackEvent.event_type, UserTrackEvent.created_at]
    form_excluded_columns = [UserTrackEvent.created_at]


class ExternalLinkClickAdmin(ModelView, model=ExternalLinkClick):
    name = "External link click"
    name_plural = "External link clicks"
    category = "Discovery"
    column_list = [
        ExternalLinkClick.id,
        ExternalLinkClick.user_id,
        ExternalLinkClick.external_link_id,
        ExternalLinkClick.track_id,
        ExternalLinkClick.created_at,
    ]
    form_excluded_columns = [ExternalLinkClick.created_at]
    can_create = False
    can_edit = False
