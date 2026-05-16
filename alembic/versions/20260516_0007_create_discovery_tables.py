"""Create discovery tables for events and recommendations.

Revision ID: 20260516_0007
Revises: 20260516_0006
Create Date: 2026-05-16 23:58:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260516_0007"
down_revision: str | None = "20260516_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRACK_EVENT_TYPE_CHECK = "event_type IN ('view', 'external_click', 'like', 'save', 'comment', 'playlist_add')"


def upgrade() -> None:
    op.create_table(
        "user_track_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(TRACK_EVENT_TYPE_CHECK, name="ck_user_track_events_event_type"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_track_events_user_created",
        "user_track_events",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_track_events_track_created",
        "user_track_events",
        ["track_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_track_events_type_created",
        "user_track_events",
        ["event_type", "created_at"],
        unique=False,
    )

    op.create_table(
        "external_link_clicks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("external_link_id", sa.Uuid(), nullable=False),
        sa.Column("track_id", sa.Uuid(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["external_link_id"], ["external_links.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_link_clicks_user_created",
        "external_link_clicks",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_external_link_clicks_link_created",
        "external_link_clicks",
        ["external_link_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_external_link_clicks_track_created",
        "external_link_clicks",
        ["track_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_external_link_clicks_track_created", table_name="external_link_clicks")
    op.drop_index("ix_external_link_clicks_link_created", table_name="external_link_clicks")
    op.drop_index("ix_external_link_clicks_user_created", table_name="external_link_clicks")
    op.drop_table("external_link_clicks")
    op.drop_index("ix_user_track_events_type_created", table_name="user_track_events")
    op.drop_index("ix_user_track_events_track_created", table_name="user_track_events")
    op.drop_index("ix_user_track_events_user_created", table_name="user_track_events")
    op.drop_table("user_track_events")
