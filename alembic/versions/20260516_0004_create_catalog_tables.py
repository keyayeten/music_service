"""Create catalog tables for tracks, albums and metadata.

Revision ID: 20260516_0004
Revises: 20260516_0003
Create Date: 2026-05-16 22:50:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260516_0004"
down_revision: str | None = "20260516_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRACK_STATUS_CHECK = "status IN ('draft', 'pending_review', 'published', 'rejected', 'hidden')"
ALBUM_STATUS_CHECK = "status IN ('draft', 'pending_review', 'published', 'rejected', 'hidden')"
ENTITY_TYPE_CHECK = "entity_type IN ('track', 'album', 'playlist')"
MUSIC_SERVICE_CHECK = (
    "service IN ('spotify', 'apple_music', 'youtube_music', 'soundcloud', "
    "'bandcamp', 'yandex_music', 'vk_music', 'other')"
)


def upgrade() -> None:
    op.create_table(
        "tracks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("plays_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("likes_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("comments_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(TRACK_STATUS_CHECK, name="ck_tracks_status"),
        sa.CheckConstraint("duration_seconds > 0", name="ck_tracks_duration_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tracks_status_published_at", "tracks", ["status", "published_at"], unique=False)
    op.create_index("ix_tracks_likes_count", "tracks", ["likes_count"], unique=False)
    op.create_index("ix_tracks_plays_count", "tracks", ["plays_count"], unique=False)

    op.create_table(
        "albums",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_composer_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("likes_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("comments_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(ALBUM_STATUS_CHECK, name="ck_albums_status"),
        sa.ForeignKeyConstraint(["owner_composer_id"], ["composer_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_albums_owner_status_release",
        "albums",
        ["owner_composer_id", "status", "release_date"],
        unique=False,
    )

    op.create_table(
        "track_authors",
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("composer_profile_id", sa.Uuid(), nullable=False),
        sa.Column("contribution_role", sa.String(length=64), server_default=sa.text("'composer'"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position > 0", name="ck_track_authors_position_positive"),
        sa.ForeignKeyConstraint(["composer_profile_id"], ["composer_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("track_id", "composer_profile_id"),
        sa.UniqueConstraint("track_id", "position", name="uq_track_authors_track_position"),
    )
    op.create_index("ix_track_authors_composer", "track_authors", ["composer_profile_id"], unique=False)

    op.create_table(
        "album_tracks",
        sa.Column("album_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("position > 0", name="ck_album_tracks_position_positive"),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("album_id", "track_id"),
        sa.UniqueConstraint("album_id", "position", name="uq_album_tracks_album_position"),
    )
    op.create_index("ix_album_tracks_album_position", "album_tracks", ["album_id", "position"], unique=False)

    op.create_table(
        "external_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("service", sa.String(length=32), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(ENTITY_TYPE_CHECK, name="ck_external_links_entity_type"),
        sa.CheckConstraint(MUSIC_SERVICE_CHECK, name="ck_external_links_service"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", "service", "url", name="uq_external_links_entity_service_url"),
    )
    op.create_index("ix_external_links_entity", "external_links", ["entity_type", "entity_id"], unique=False)
    op.create_index("ix_external_links_service", "external_links", ["service"], unique=False)

    op.create_table(
        "genres",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_genres_code"),
    )

    op.create_table(
        "track_genres",
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("genre_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["genre_id"], ["genres.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("track_id", "genre_id"),
    )
    op.create_index("ix_track_genres_genre", "track_genres", ["genre_id"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_tags_slug"),
    )

    op.create_table(
        "entity_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(ENTITY_TYPE_CHECK, name="ck_entity_tags_entity_type"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tag_id", "entity_type", "entity_id", name="uq_entity_tags_tag_entity"),
    )
    op.create_index("ix_entity_tags_entity", "entity_tags", ["entity_type", "entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_entity_tags_entity", table_name="entity_tags")
    op.drop_table("entity_tags")
    op.drop_table("tags")
    op.drop_index("ix_track_genres_genre", table_name="track_genres")
    op.drop_table("track_genres")
    op.drop_table("genres")
    op.drop_index("ix_external_links_service", table_name="external_links")
    op.drop_index("ix_external_links_entity", table_name="external_links")
    op.drop_table("external_links")
    op.drop_index("ix_album_tracks_album_position", table_name="album_tracks")
    op.drop_table("album_tracks")
    op.drop_index("ix_track_authors_composer", table_name="track_authors")
    op.drop_table("track_authors")
    op.drop_index("ix_albums_owner_status_release", table_name="albums")
    op.drop_table("albums")
    op.drop_index("ix_tracks_plays_count", table_name="tracks")
    op.drop_index("ix_tracks_likes_count", table_name="tracks")
    op.drop_index("ix_tracks_status_published_at", table_name="tracks")
    op.drop_table("tracks")
