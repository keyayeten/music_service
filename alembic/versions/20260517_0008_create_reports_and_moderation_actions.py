"""Create reports and moderation actions tables.

Revision ID: 20260517_0008
Revises: 20260516_0007
Create Date: 2026-05-17 00:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260517_0008"
down_revision: str | None = "20260516_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPORT_TARGET_TYPE_CHECK = "target_type IN ('track', 'album', 'playlist', 'comment')"
REPORT_STATUS_CHECK = "status IN ('open', 'in_review', 'resolved', 'rejected')"
MODERATION_ACTION_TARGET_TYPE_CHECK = "target_type IN ('track', 'album', 'playlist', 'comment', 'report')"


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'open'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(REPORT_TARGET_TYPE_CHECK, name="ck_reports_target_type"),
        sa.CheckConstraint(REPORT_STATUS_CHECK, name="ck_reports_status"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_status_created", "reports", ["status", "created_at"], unique=False)
    op.create_index("ix_reports_target", "reports", ["target_type", "target_id"], unique=False)

    op.create_table(
        "moderation_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(MODERATION_ACTION_TARGET_TYPE_CHECK, name="ck_moderation_actions_target_type"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_moderation_actions_actor_created",
        "moderation_actions",
        ["actor_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_moderation_actions_target_created",
        "moderation_actions",
        ["target_type", "target_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_moderation_actions_target_created", table_name="moderation_actions")
    op.drop_index("ix_moderation_actions_actor_created", table_name="moderation_actions")
    op.drop_table("moderation_actions")
    op.drop_index("ix_reports_target", table_name="reports")
    op.drop_index("ix_reports_status_created", table_name="reports")
    op.drop_table("reports")
