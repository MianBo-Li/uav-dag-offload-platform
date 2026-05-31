"""create schedule plan tables

Revision ID: 20260531_0004
Revises: 20260526_0003
Create Date: 2026-05-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260531_0004"
down_revision: str | None = "20260526_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "schedule_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("estimated_total_duration_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_total_energy", sa.Numeric(14, 4), nullable=True),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "strategy_name in ('local_only', 'random_offload', 'greedy')",
            name="ck_schedule_plans_strategy_name",
        ),
        sa.CheckConstraint(
            "status in ('GENERATED', 'APPLIED', 'CANCELED')",
            name="ck_schedule_plans_status",
        ),
        sa.CheckConstraint(
            "estimated_total_duration_ms is null or estimated_total_duration_ms >= 0",
            name="ck_schedule_plans_duration_non_negative",
        ),
        sa.CheckConstraint(
            "estimated_total_energy is null or estimated_total_energy >= 0",
            name="ck_schedule_plans_energy_non_negative",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["dag_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_plans_task_id", "schedule_plans", ["task_id"])
    op.create_index(
        "idx_schedule_plans_task_created",
        "schedule_plans",
        ["task_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_schedule_plans_strategy",
        "schedule_plans",
        ["strategy_name"],
    )

    op.create_table(
        "schedule_plan_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("subtask_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_node_id", sa.Uuid(), nullable=False),
        sa.Column("estimated_compute_duration_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_transfer_duration_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_energy", sa.Numeric(14, 4), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "estimated_compute_duration_ms is null "
                "or estimated_compute_duration_ms >= 0"
            ),
            name="ck_schedule_items_compute_duration_non_negative",
        ),
        sa.CheckConstraint(
            (
                "estimated_transfer_duration_ms is null "
                "or estimated_transfer_duration_ms >= 0"
            ),
            name="ck_schedule_items_transfer_duration_non_negative",
        ),
        sa.CheckConstraint(
            "estimated_energy is null or estimated_energy >= 0",
            name="ck_schedule_items_energy_non_negative",
        ),
        sa.ForeignKeyConstraint(["assigned_node_id"], ["nodes.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["schedule_plans.id"]),
        sa.ForeignKeyConstraint(["subtask_id"], ["dag_subtasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "subtask_id", name="uq_schedule_items_plan_subtask"),
    )
    op.create_index("ix_schedule_plan_items_plan_id", "schedule_plan_items", ["plan_id"])
    op.create_index(
        "ix_schedule_plan_items_subtask_id",
        "schedule_plan_items",
        ["subtask_id"],
    )
    op.create_index(
        "ix_schedule_plan_items_assigned_node_id",
        "schedule_plan_items",
        ["assigned_node_id"],
    )
    op.create_index("idx_schedule_items_plan", "schedule_plan_items", ["plan_id"])
    op.create_index("idx_schedule_items_subtask", "schedule_plan_items", ["subtask_id"])
    op.create_index(
        "idx_schedule_items_node",
        "schedule_plan_items",
        ["assigned_node_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_schedule_items_node", table_name="schedule_plan_items")
    op.drop_index("idx_schedule_items_subtask", table_name="schedule_plan_items")
    op.drop_index("idx_schedule_items_plan", table_name="schedule_plan_items")
    op.drop_index("ix_schedule_plan_items_assigned_node_id", table_name="schedule_plan_items")
    op.drop_index("ix_schedule_plan_items_subtask_id", table_name="schedule_plan_items")
    op.drop_index("ix_schedule_plan_items_plan_id", table_name="schedule_plan_items")
    op.drop_table("schedule_plan_items")

    op.drop_index("idx_schedule_plans_strategy", table_name="schedule_plans")
    op.drop_index("idx_schedule_plans_task_created", table_name="schedule_plans")
    op.drop_index("ix_schedule_plans_task_id", table_name="schedule_plans")
    op.drop_table("schedule_plans")
