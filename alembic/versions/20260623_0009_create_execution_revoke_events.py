"""create execution revoke events

Revision ID: 20260623_0009
Revises: 20260622_0008
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260623_0009"
down_revision: str | None = "20260622_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_revoke_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["execution_id"], ["execution_records.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["dag_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_execution_revoke_events_task_id",
        "execution_revoke_events",
        ["task_id"],
    )
    op.create_index(
        "idx_execution_revoke_events_execution_id",
        "execution_revoke_events",
        ["execution_id"],
    )
    op.create_index(
        "idx_execution_revoke_events_celery_task_id",
        "execution_revoke_events",
        ["celery_task_id"],
    )
    op.create_index(
        "idx_execution_revoke_events_requested_at",
        "execution_revoke_events",
        [sa.text("requested_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_execution_revoke_events_requested_at",
        table_name="execution_revoke_events",
    )
    op.drop_index(
        "idx_execution_revoke_events_celery_task_id",
        table_name="execution_revoke_events",
    )
    op.drop_index(
        "idx_execution_revoke_events_execution_id",
        table_name="execution_revoke_events",
    )
    op.drop_index("idx_execution_revoke_events_task_id", table_name="execution_revoke_events")
    op.drop_table("execution_revoke_events")
