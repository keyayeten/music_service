"""SQLAlchemy ORM models package."""

from backend.infrastructure.persistence.models.base import Base
from backend.infrastructure.persistence.models.catalog import (
    Album,
    AlbumTrack,
    EntityTag,
    ExternalLink,
    Genre,
    Tag,
    Track,
    TrackAuthor,
    TrackGenre,
)
from backend.infrastructure.persistence.models.discovery import ExternalLinkClick, UserTrackEvent
from backend.infrastructure.persistence.models.identity import (
    ComposerProfile,
    Role,
    User,
    UserRole,
    UserRoleProfile,
)
from backend.infrastructure.persistence.models.library import LibraryItem, Playlist, PlaylistTrack
from backend.infrastructure.persistence.models.moderation import ModerationAction, Report
from backend.infrastructure.persistence.models.service_heartbeat import ServiceHeartbeat
from backend.infrastructure.persistence.models.social import Comment, Like

__all__ = [
    "Base",
    "ServiceHeartbeat",
    "User",
    "Role",
    "UserRole",
    "ComposerProfile",
    "UserRoleProfile",
    "Track",
    "TrackAuthor",
    "Album",
    "AlbumTrack",
    "ExternalLink",
    "Genre",
    "TrackGenre",
    "Tag",
    "EntityTag",
    "UserTrackEvent",
    "ExternalLinkClick",
    "Playlist",
    "PlaylistTrack",
    "LibraryItem",
    "Report",
    "ModerationAction",
    "Comment",
    "Like",
]
