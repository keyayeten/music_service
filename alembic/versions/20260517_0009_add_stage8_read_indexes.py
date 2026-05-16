"""Add Stage 8 read path indexes.

Revision ID: 20260517_0009
Revises: 20260517_0008
Create Date: 2026-05-17 00:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260517_0009"
down_revision: str | None = "20260517_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_users_status_created_at", "users", ["status", "created_at"], unique=False)
    op.create_index("ix_playlists_visibility_created", "playlists", ["visibility", "created_at"], unique=False)
    op.create_index(
        "ix_comments_visible_target_created",
        "comments",
        ["target_type", "target_id", "created_at"],
        unique=False,
        postgresql_where=sa.text("status = 'visible'"),
    )

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_tracks_title_trgm",
        "tracks",
        ["title"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_composer_profiles_display_name_trgm",
        "composer_profiles",
        ["display_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"display_name": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_composer_profiles_display_name_trgm", table_name="composer_profiles")
    op.drop_index("ix_tracks_title_trgm", table_name="tracks")
    op.drop_index("ix_comments_visible_target_created", table_name="comments")
    op.drop_index("ix_playlists_visibility_created", table_name="playlists")
    op.drop_index("ix_users_status_created_at", table_name="users")
