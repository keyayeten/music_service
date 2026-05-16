"""Create library tables for playlists and user library items.

Revision ID: 20260516_0005
Revises: 20260516_0004
Create Date: 2026-05-16 23:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260516_0005"
down_revision: str | None = "20260516_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLAYLIST_VISIBILITY_CHECK = "visibility IN ('private', 'unlisted', 'public')"
LIBRARY_ITEM_TYPE_CHECK = "item_type IN ('track', 'album', 'playlist')"
LIBRARY_SECTION_CHECK = "section IN ('favorites', 'albums', 'playlists')"


def upgrade() -> None:
    op.create_table(
        "playlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=32), server_default=sa.text("'private'"), nullable=False),
        sa.Column("likes_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("comments_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(PLAYLIST_VISIBILITY_CHECK, name="ck_playlists_visibility"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_playlists_owner_created", "playlists", ["owner_user_id", "created_at"], unique=False)
    op.create_index("ix_playlists_visibility_likes", "playlists", ["visibility", "likes_count"], unique=False)

    op.create_table(
        "playlist_tracks",
        sa.Column("playlist_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("added_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("position > 0", name="ck_playlist_tracks_position_positive"),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("playlist_id", "track_id"),
        sa.UniqueConstraint("playlist_id", "position", name="uq_playlist_tracks_playlist_position"),
    )
    op.create_index(
        "ix_playlist_tracks_playlist_position",
        "playlist_tracks",
        ["playlist_id", "position"],
        unique=False,
    )

    op.create_table(
        "library_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("section", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(LIBRARY_ITEM_TYPE_CHECK, name="ck_library_items_item_type"),
        sa.CheckConstraint(LIBRARY_SECTION_CHECK, name="ck_library_items_section"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "item_type", "item_id", name="uq_library_items_user_item"),
    )
    op.create_index(
        "ix_library_items_user_section_created",
        "library_items",
        ["user_id", "section", "created_at"],
        unique=False,
    )
    op.create_index("ix_library_items_item", "library_items", ["item_type", "item_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_library_items_item", table_name="library_items")
    op.drop_index("ix_library_items_user_section_created", table_name="library_items")
    op.drop_table("library_items")
    op.drop_index("ix_playlist_tracks_playlist_position", table_name="playlist_tracks")
    op.drop_table("playlist_tracks")
    op.drop_index("ix_playlists_visibility_likes", table_name="playlists")
    op.drop_index("ix_playlists_owner_created", table_name="playlists")
    op.drop_table("playlists")
