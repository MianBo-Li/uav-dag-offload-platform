"""add execution celery task id

Revision ID: 20260622_0008
Revises: 20260622_0007
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260622_0008"
down_revision: str | None = "20260622_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "execution_records",
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "idx_execution_records_celery_task_id",
        "execution_records",
        ["celery_task_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_execution_records_celery_task_id", table_name="execution_records")
    op.drop_column("execution_records", "celery_task_id")
