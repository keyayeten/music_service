from sqladmin import ModelView

from backend.infrastructure.persistence.models.library import LibraryItem, Playlist, PlaylistTrack

_PLAYLIST_COUNTER_COLUMNS = ("likes_count", "comments_count")


class PlaylistAdmin(ModelView, model=Playlist):
    name = "Playlist"
    name_plural = "Playlists"
    category = "Library"
    column_list = [Playlist.id, Playlist.title, Playlist.visibility, Playlist.owner_user_id, Playlist.created_at]
    column_searchable_list = [Playlist.title]
    form_excluded_columns = [Playlist.created_at, Playlist.updated_at, Playlist.deleted_at, *_PLAYLIST_COUNTER_COLUMNS]


class PlaylistTrackAdmin(ModelView, model=PlaylistTrack):
    name = "Playlist track"
    name_plural = "Playlist tracks"
    category = "Library"
    column_list = [PlaylistTrack.playlist_id, PlaylistTrack.track_id, PlaylistTrack.position, PlaylistTrack.added_at]
    form_excluded_columns = [PlaylistTrack.added_at]


class LibraryItemAdmin(ModelView, model=LibraryItem):
    name = "Library item"
    name_plural = "Library items"
    category = "Library"
    column_list = [LibraryItem.id, LibraryItem.user_id, LibraryItem.item_type, LibraryItem.item_id, LibraryItem.section]
    form_excluded_columns = [LibraryItem.created_at]
