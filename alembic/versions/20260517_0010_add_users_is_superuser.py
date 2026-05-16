"""Add users.is_superuser column.

Revision ID: 20260517_0010
Revises: 20260517_0009
Create Date: 2026-05-17 12:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260517_0010"
down_revision: str | None = "20260517_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "is_superuser")
