"""add canceled subtask status

Revision ID: 20260610_0006
Revises: 20260531_0005
Create Date: 2026-06-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260610_0006"
down_revision: str | None = "20260531_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_dag_subtasks_status", "dag_subtasks", type_="check")
    op.create_check_constraint(
        "ck_dag_subtasks_status",
        "dag_subtasks",
        "status in ('WAITING', 'READY', 'DISPATCHED', 'RUNNING', "
        "'SUCCESS', 'FAILED', 'RETRYING', 'CANCELED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_dag_subtasks_status", "dag_subtasks", type_="check")
    op.create_check_constraint(
        "ck_dag_subtasks_status",
        "dag_subtasks",
        "status in ('WAITING', 'READY', 'DISPATCHED', 'RUNNING', "
        "'SUCCESS', 'FAILED', 'RETRYING')",
    )
