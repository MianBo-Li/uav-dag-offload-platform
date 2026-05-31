"""add subtask execution constraint

Revision ID: 20260526_0003
Revises: 20260524_0002
Create Date: 2026-05-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260526_0003"
down_revision: str | None = "20260524_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dag_subtasks",
        sa.Column(
            "execution_constraint",
            sa.String(length=16),
            nullable=False,
            server_default="OFFLOADABLE",
        ),
    )
    op.create_check_constraint(
        "ck_dag_subtasks_execution_constraint",
        "dag_subtasks",
        "execution_constraint in ('OFFLOADABLE', 'LOCAL_ONLY', 'EDGE_ONLY')",
    )
    op.alter_column("dag_subtasks", "execution_constraint", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_dag_subtasks_execution_constraint",
        "dag_subtasks",
        type_="check",
    )
    op.drop_column("dag_subtasks", "execution_constraint")
