from sqladmin import ModelView

from backend.infrastructure.admin.views.catalog import (
    AlbumAdmin,
    AlbumTrackAdmin,
    EntityTagAdmin,
    ExternalLinkAdmin,
    GenreAdmin,
    TagAdmin,
    TrackAdmin,
    TrackAuthorAdmin,
    TrackGenreAdmin,
)
from backend.infrastructure.admin.views.discovery import ExternalLinkClickAdmin, UserTrackEventAdmin
from backend.infrastructure.admin.views.identity import (
    ComposerProfileAdmin,
    RoleAdmin,
    UserAdmin,
    UserRoleAdmin,
    UserRoleProfileAdmin,
)
from backend.infrastructure.admin.views.library import (
    LibraryItemAdmin,
    PlaylistAdmin,
    PlaylistTrackAdmin,
)
from backend.infrastructure.admin.views.moderation import ModerationActionAdmin, ReportAdmin
from backend.infrastructure.admin.views.ops import ServiceHeartbeatAdmin
from backend.infrastructure.admin.views.social import CommentAdmin, LikeAdmin


def get_admin_views() -> list[type[ModelView]]:
    return [
        UserAdmin,
        RoleAdmin,
        UserRoleAdmin,
        ComposerProfileAdmin,
        UserRoleProfileAdmin,
        TrackAdmin,
        TrackAuthorAdmin,
        AlbumAdmin,
        AlbumTrackAdmin,
        ExternalLinkAdmin,
        GenreAdmin,
        TrackGenreAdmin,
        TagAdmin,
        EntityTagAdmin,
        PlaylistAdmin,
        PlaylistTrackAdmin,
        LibraryItemAdmin,
        CommentAdmin,
        LikeAdmin,
        UserTrackEventAdmin,
        ExternalLinkClickAdmin,
        ReportAdmin,
        ModerationActionAdmin,
        ServiceHeartbeatAdmin,
    ]
