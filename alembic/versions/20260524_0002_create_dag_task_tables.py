"""create dag task tables

Revision ID: 20260524_0002
Revises: 20260521_0001
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260524_0002"
down_revision: str | None = "20260521_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dag_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", sa.String(length=128), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('PENDING', 'SCHEDULED', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELED')",
            name="ck_dag_tasks_status",
        ),
        sa.CheckConstraint("priority >= 0", name="ck_dag_tasks_priority_non_negative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dag_tasks_status", "dag_tasks", ["status"])
    op.create_index("idx_dag_tasks_created_at", "dag_tasks", [sa.text("created_at DESC")])
    op.create_index("idx_dag_tasks_priority_status", "dag_tasks", [sa.text("priority DESC"), "status"])

    op.create_table(
        "dag_subtasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("compute_load", sa.Numeric(12, 2), nullable=False),
        sa.Column("input_data_size_mb", sa.Numeric(12, 2), nullable=False),
        sa.Column("output_data_size_mb", sa.Numeric(12, 2), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('WAITING', 'READY', 'DISPATCHED', 'RUNNING', 'SUCCESS', 'FAILED', 'RETRYING')",
            name="ck_dag_subtasks_status",
        ),
        sa.CheckConstraint("compute_load > 0", name="ck_dag_subtasks_compute_load_positive"),
        sa.CheckConstraint("input_data_size_mb >= 0", name="ck_dag_subtasks_input_non_negative"),
        sa.CheckConstraint("output_data_size_mb >= 0", name="ck_dag_subtasks_output_non_negative"),
        sa.CheckConstraint("max_retries >= 0", name="ck_dag_subtasks_max_retries_non_negative"),
        sa.CheckConstraint("retry_count >= 0", name="ck_dag_subtasks_retry_count_non_negative"),
        sa.ForeignKeyConstraint(["task_id"], ["dag_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "external_id", name="uq_dag_subtasks_task_external"),
    )
    op.create_index("ix_dag_subtasks_task_id", "dag_subtasks", ["task_id"])
    op.create_index("idx_dag_subtasks_task_status", "dag_subtasks", ["task_id", "status"])
    op.create_index("idx_dag_subtasks_task_external", "dag_subtasks", ["task_id", "external_id"])

    op.create_table(
        "dag_dependencies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("predecessor_subtask_id", sa.Uuid(), nullable=False),
        sa.Column("successor_subtask_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "predecessor_subtask_id <> successor_subtask_id",
            name="ck_dag_dependencies_not_self",
        ),
        sa.ForeignKeyConstraint(["predecessor_subtask_id"], ["dag_subtasks.id"]),
        sa.ForeignKeyConstraint(["successor_subtask_id"], ["dag_subtasks.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["dag_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id",
            "predecessor_subtask_id",
            "successor_subtask_id",
            name="uq_dag_dependencies_task_edge",
        ),
    )
    op.create_index("ix_dag_dependencies_task_id", "dag_dependencies", ["task_id"])
    op.create_index(
        "ix_dag_dependencies_predecessor_subtask_id",
        "dag_dependencies",
        ["predecessor_subtask_id"],
    )
    op.create_index(
        "ix_dag_dependencies_successor_subtask_id",
        "dag_dependencies",
        ["successor_subtask_id"],
    )
    op.create_index("idx_dag_dependencies_task", "dag_dependencies", ["task_id"])
    op.create_index(
        "idx_dag_dependencies_predecessor",
        "dag_dependencies",
        ["predecessor_subtask_id"],
    )
    op.create_index(
        "idx_dag_dependencies_successor",
        "dag_dependencies",
        ["successor_subtask_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_dag_dependencies_successor", table_name="dag_dependencies")
    op.drop_index("idx_dag_dependencies_predecessor", table_name="dag_dependencies")
    op.drop_index("idx_dag_dependencies_task", table_name="dag_dependencies")
    op.drop_index("ix_dag_dependencies_successor_subtask_id", table_name="dag_dependencies")
    op.drop_index("ix_dag_dependencies_predecessor_subtask_id", table_name="dag_dependencies")
    op.drop_index("ix_dag_dependencies_task_id", table_name="dag_dependencies")
    op.drop_table("dag_dependencies")

    op.drop_index("idx_dag_subtasks_task_external", table_name="dag_subtasks")
    op.drop_index("idx_dag_subtasks_task_status", table_name="dag_subtasks")
    op.drop_index("ix_dag_subtasks_task_id", table_name="dag_subtasks")
    op.drop_table("dag_subtasks")

    op.drop_index("idx_dag_tasks_priority_status", table_name="dag_tasks")
    op.drop_index("idx_dag_tasks_created_at", table_name="dag_tasks")
    op.drop_index("idx_dag_tasks_status", table_name="dag_tasks")
    op.drop_table("dag_tasks")
