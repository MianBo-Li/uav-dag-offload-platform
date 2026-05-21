"""create node tables

Revision ID: 20260521_0001
Revises:
Create Date: 2026-05-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260521_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("node_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("cpu_capacity", sa.Numeric(10, 2), nullable=False),
        sa.Column("memory_capacity_mb", sa.Integer(), nullable=False),
        sa.Column("network_address", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("node_type in ('UAV', 'EDGE')", name="ck_nodes_node_type"),
        sa.CheckConstraint("status in ('ONLINE', 'BUSY', 'OFFLINE')", name="ck_nodes_status"),
        sa.CheckConstraint("cpu_capacity > 0", name="ck_nodes_cpu_capacity_positive"),
        sa.CheckConstraint("memory_capacity_mb > 0", name="ck_nodes_memory_capacity_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_nodes_name"),
    )
    op.create_index("ix_nodes_name", "nodes", ["name"])
    op.create_index("idx_nodes_type_status", "nodes", ["node_type", "status"])
    op.create_index("idx_nodes_last_heartbeat", "nodes", ["last_heartbeat_at"])

    op.create_table(
        "node_status_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("battery_level", sa.Numeric(5, 2), nullable=True),
        sa.Column("cpu_usage", sa.Numeric(5, 2), nullable=False),
        sa.Column("memory_usage", sa.Numeric(5, 2), nullable=False),
        sa.Column("network_quality", sa.Numeric(5, 2), nullable=True),
        sa.Column("bandwidth_mbps", sa.Numeric(10, 2), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("current_load", sa.Integer(), nullable=True),
        sa.Column("queue_length", sa.Integer(), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("cpu_usage between 0 and 100", name="ck_node_status_cpu_usage_range"),
        sa.CheckConstraint(
            "memory_usage between 0 and 100",
            name="ck_node_status_memory_usage_range",
        ),
        sa.CheckConstraint(
            "battery_level is null or battery_level between 0 and 100",
            name="ck_node_status_battery_range",
        ),
        sa.CheckConstraint(
            "network_quality is null or network_quality between 0 and 100",
            name="ck_node_status_network_quality_range",
        ),
        sa.CheckConstraint(
            "bandwidth_mbps is null or bandwidth_mbps >= 0",
            name="ck_node_status_bandwidth_non_negative",
        ),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_node_status_records_node_id", "node_status_records", ["node_id"])
    op.create_index(
        "idx_node_status_node_time",
        "node_status_records",
        ["node_id", sa.text("reported_at DESC")],
    )
    op.create_index("idx_node_status_reported_at", "node_status_records", ["reported_at"])


def downgrade() -> None:
    op.drop_index("idx_node_status_reported_at", table_name="node_status_records")
    op.drop_index("idx_node_status_node_time", table_name="node_status_records")
    op.drop_index("ix_node_status_records_node_id", table_name="node_status_records")
    op.drop_table("node_status_records")

    op.drop_index("idx_nodes_last_heartbeat", table_name="nodes")
    op.drop_index("idx_nodes_type_status", table_name="nodes")
    op.drop_index("ix_nodes_name", table_name="nodes")
    op.drop_table("nodes")
