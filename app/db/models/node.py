from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import NodeStatus, NodeType


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    node_type: Mapped[NodeType] = mapped_column(String(16), nullable=False)
    status: Mapped[NodeStatus] = mapped_column(
        String(16), nullable=False, default=NodeStatus.ONLINE
    )
    cpu_capacity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    memory_capacity_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    network_address: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    status_records: Mapped[list["NodeStatusRecord"]] = relationship(
        back_populates="node",
        cascade="all, delete-orphan",
    )


class NodeStatusRecord(Base):
    __tablename__ = "node_status_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    node_id: Mapped[UUID] = mapped_column(ForeignKey("nodes.id"), nullable=False, index=True)
    battery_level: Mapped[float | None] = mapped_column(Numeric(5, 2))
    cpu_usage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    memory_usage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    network_quality: Mapped[float | None] = mapped_column(Numeric(5, 2))
    bandwidth_mbps: Mapped[float | None] = mapped_column(Numeric(10, 2))
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    current_load: Mapped[int | None] = mapped_column(Integer)
    queue_length: Mapped[int | None] = mapped_column(Integer)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    node: Mapped[Node] = relationship(back_populates="status_records")
