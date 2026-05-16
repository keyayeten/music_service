"""Create social tables for likes and comments.

Revision ID: 20260516_0006
Revises: 20260516_0005
Create Date: 2026-05-16 23:45:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260516_0006"
down_revision: str | None = "20260516_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOCIAL_TARGET_TYPE_CHECK = "target_type IN ('track', 'album', 'playlist')"
COMMENT_STATUS_CHECK = "status IN ('visible', 'hidden', 'deleted', 'pending_review')"


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("parent_comment_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'visible'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(SOCIAL_TARGET_TYPE_CHECK, name="ck_comments_target_type"),
        sa.CheckConstraint(COMMENT_STATUS_CHECK, name="ck_comments_status"),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["comments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comments_target_created",
        "comments",
        ["target_type", "target_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_comments_user_created", "comments", ["user_id", "created_at"], unique=False)
    op.create_index("ix_comments_parent", "comments", ["parent_comment_id"], unique=False)

    op.create_table(
        "likes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(SOCIAL_TARGET_TYPE_CHECK, name="ck_likes_target_type"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "target_type", "target_id", name="uq_likes_user_target"),
    )
    op.create_index(
        "ix_likes_target_created",
        "likes",
        ["target_type", "target_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_likes_user_created", "likes", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_likes_user_created", table_name="likes")
    op.drop_index("ix_likes_target_created", table_name="likes")
    op.drop_table("likes")
    op.drop_index("ix_comments_parent", table_name="comments")
    op.drop_index("ix_comments_user_created", table_name="comments")
    op.drop_index("ix_comments_target_created", table_name="comments")
    op.drop_table("comments")
