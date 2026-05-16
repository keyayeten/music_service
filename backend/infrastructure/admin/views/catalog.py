from sqladmin import ModelView

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

_COUNTER_COLUMNS = (
    "plays_count",
    "likes_count",
    "comments_count",
)


class TrackAdmin(ModelView, model=Track):
    name = "Track"
    name_plural = "Tracks"
    category = "Catalog"
    column_list = [Track.id, Track.title, Track.status, Track.duration_seconds, Track.published_at]
    column_searchable_list = [Track.title]
    column_sortable_list = [Track.title, Track.status, Track.published_at, Track.created_at]
    form_excluded_columns = [Track.created_at, Track.updated_at, Track.deleted_at, *_COUNTER_COLUMNS]


class TrackAuthorAdmin(ModelView, model=TrackAuthor):
    name = "Track author"
    name_plural = "Track authors"
    category = "Catalog"
    column_list = [TrackAuthor.track_id, TrackAuthor.composer_profile_id, TrackAuthor.position, TrackAuthor.contribution_role]


class AlbumAdmin(ModelView, model=Album):
    name = "Album"
    name_plural = "Albums"
    category = "Catalog"
    column_list = [Album.id, Album.title, Album.status, Album.release_date, Album.owner_composer_id]
    column_searchable_list = [Album.title]
    form_excluded_columns = [Album.created_at, Album.updated_at, Album.deleted_at, "likes_count", "comments_count"]


class AlbumTrackAdmin(ModelView, model=AlbumTrack):
    name = "Album track"
    name_plural = "Album tracks"
    category = "Catalog"
    column_list = [AlbumTrack.album_id, AlbumTrack.track_id, AlbumTrack.position]


class ExternalLinkAdmin(ModelView, model=ExternalLink):
    name = "External link"
    name_plural = "External links"
    category = "Catalog"
    column_list = [ExternalLink.id, ExternalLink.entity_type, ExternalLink.entity_id, ExternalLink.service, ExternalLink.url]
    column_searchable_list = [ExternalLink.url, ExternalLink.service]
    form_excluded_columns = [ExternalLink.created_at]


class GenreAdmin(ModelView, model=Genre):
    name = "Genre"
    name_plural = "Genres"
    category = "Catalog"
    column_list = [Genre.id, Genre.code, Genre.name]
    column_searchable_list = [Genre.code, Genre.name]
    form_excluded_columns = [Genre.created_at]


class TrackGenreAdmin(ModelView, model=TrackGenre):
    name = "Track genre"
    name_plural = "Track genres"
    category = "Catalog"
    column_list = [TrackGenre.track_id, TrackGenre.genre_id]


class TagAdmin(ModelView, model=Tag):
    name = "Tag"
    name_plural = "Tags"
    category = "Catalog"
    column_list = [Tag.id, Tag.slug, Tag.name]
    column_searchable_list = [Tag.slug, Tag.name]
    form_excluded_columns = [Tag.created_at]


class EntityTagAdmin(ModelView, model=EntityTag):
    name = "Entity tag"
    name_plural = "Entity tags"
    category = "Catalog"
    column_list = [EntityTag.id, EntityTag.tag_id, EntityTag.entity_type, EntityTag.entity_id]
    form_excluded_columns = [EntityTag.created_at]
