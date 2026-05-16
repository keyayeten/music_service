"""Create service_heartbeats table.

Revision ID: 20260516_0001
Revises: 
Create Date: 2026-05-16 21:45:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260516_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_heartbeats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_heartbeats_source", "service_heartbeats", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_service_heartbeats_source", table_name="service_heartbeats")
    op.drop_table("service_heartbeats")
