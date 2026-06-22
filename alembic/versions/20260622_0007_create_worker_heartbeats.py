"""create worker heartbeats

Revision ID: 20260622_0007
Revises: 20260610_0006
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260622_0007"
down_revision: str | None = "20260610_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "worker_heartbeats",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("worker_name", sa.String(length=128), nullable=False),
        sa.Column("hostname", sa.String(length=128), nullable=False),
        sa.Column("process_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("current_execution_id", sa.Uuid(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('ONLINE', 'BUSY')",
            name="ck_worker_heartbeats_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_name", name="uq_worker_heartbeats_worker_name"),
    )
    op.create_index("idx_worker_heartbeats_status", "worker_heartbeats", ["status"])
    op.create_index(
        "idx_worker_heartbeats_last_seen_at",
        "worker_heartbeats",
        [sa.text("last_seen_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_worker_heartbeats_last_seen_at", table_name="worker_heartbeats")
    op.drop_index("idx_worker_heartbeats_status", table_name="worker_heartbeats")
    op.drop_table("worker_heartbeats")
