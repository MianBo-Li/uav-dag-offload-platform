"""create worker alerts

Revision ID: 20260623_0010
Revises: 20260623_0009
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260623_0010"
down_revision: str | None = "20260623_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "worker_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("worker_name", sa.String(length=128), nullable=True),
        sa.Column("execution_id", sa.Uuid(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "alert_type in ('CELERY_RETRY_EXHAUSTED')",
            name="ck_worker_alerts_alert_type",
        ),
        sa.CheckConstraint(
            "severity in ('WARNING', 'ERROR')",
            name="ck_worker_alerts_severity",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_worker_alerts_execution_id", "worker_alerts", ["execution_id"])
    op.create_index(
        "idx_worker_alerts_celery_task_id",
        "worker_alerts",
        ["celery_task_id"],
    )
    op.create_index("idx_worker_alerts_alert_type", "worker_alerts", ["alert_type"])


def downgrade() -> None:
    op.drop_index("idx_worker_alerts_alert_type", table_name="worker_alerts")
    op.drop_index("idx_worker_alerts_celery_task_id", table_name="worker_alerts")
    op.drop_index("idx_worker_alerts_execution_id", table_name="worker_alerts")
    op.drop_table("worker_alerts")
