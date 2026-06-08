from sqladmin import ModelView

from backend.infrastructure.persistence.models.service_heartbeat import ServiceHeartbeat


class ServiceHeartbeatAdmin(ModelView, model=ServiceHeartbeat):
    name = "Service heartbeat"
    name_plural = "Service heartbeats"
    category = "Operations"
    column_list = [
        ServiceHeartbeat.id,
        ServiceHeartbeat.source,
        ServiceHeartbeat.status,
        ServiceHeartbeat.created_at,
    ]
    column_sortable_list = [ServiceHeartbeat.created_at, ServiceHeartbeat.source]
    form_excluded_columns = [ServiceHeartbeat.created_at]
