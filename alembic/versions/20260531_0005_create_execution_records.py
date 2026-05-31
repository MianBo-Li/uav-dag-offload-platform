"""create execution records

Revision ID: 20260531_0005
Revises: 20260531_0004
Create Date: 2026-05-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260531_0005"
down_revision: str | None = "20260531_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("subtask_id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("plan_item_id", sa.Uuid(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
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
        sa.CheckConstraint("attempt >= 1", name="ck_execution_records_attempt_positive"),
        sa.CheckConstraint(
            "status in ('RUNNING', 'SUCCESS', 'FAILED', 'TIMEOUT', 'CANCELED')",
            name="ck_execution_records_status",
        ),
        sa.CheckConstraint(
            "duration_ms is null or duration_ms >= 0",
            name="ck_execution_records_duration_non_negative",
        ),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
        sa.ForeignKeyConstraint(["plan_item_id"], ["schedule_plan_items.id"]),
        sa.ForeignKeyConstraint(["subtask_id"], ["dag_subtasks.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["dag_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subtask_id", "attempt", name="uq_execution_subtask_attempt"),
    )
    op.create_index("ix_execution_records_task_id", "execution_records", ["task_id"])
    op.create_index("ix_execution_records_subtask_id", "execution_records", ["subtask_id"])
    op.create_index("ix_execution_records_node_id", "execution_records", ["node_id"])
    op.create_index(
        "ix_execution_records_plan_item_id",
        "execution_records",
        ["plan_item_id"],
    )
    op.create_index("idx_execution_records_task", "execution_records", ["task_id"])
    op.create_index("idx_execution_records_subtask", "execution_records", ["subtask_id"])
    op.create_index("idx_execution_records_node", "execution_records", ["node_id"])
    op.create_index("idx_execution_records_status", "execution_records", ["status"])


def downgrade() -> None:
    op.drop_index("idx_execution_records_status", table_name="execution_records")
    op.drop_index("idx_execution_records_node", table_name="execution_records")
    op.drop_index("idx_execution_records_subtask", table_name="execution_records")
    op.drop_index("idx_execution_records_task", table_name="execution_records")
    op.drop_index("ix_execution_records_plan_item_id", table_name="execution_records")
    op.drop_index("ix_execution_records_node_id", table_name="execution_records")
    op.drop_index("ix_execution_records_subtask_id", table_name="execution_records")
    op.drop_index("ix_execution_records_task_id", table_name="execution_records")
    op.drop_table("execution_records")
