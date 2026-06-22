from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    ExecutionStatus,
    SchedulePlanStatus,
    SchedulerStrategyName,
    SubtaskExecutionConstraint,
    SubtaskStatus,
    TaskStatus,
)


class DagTask(Base):
    __tablename__ = "dag_tasks"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        String(16), nullable=False, default=TaskStatus.PENDING
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_by: Mapped[str | None] = mapped_column(String(128))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    subtasks: Mapped[list["DagSubtask"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    dependencies: Mapped[list["DagDependency"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    schedule_plans: Mapped[list["SchedulePlan"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    execution_records: Mapped[list["ExecutionRecord"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )


class DagSubtask(Base):
    __tablename__ = "dag_subtasks"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("dag_tasks.id"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[SubtaskStatus] = mapped_column(String(16), nullable=False)
    execution_constraint: Mapped[SubtaskExecutionConstraint] = mapped_column(
        String(16),
        nullable=False,
        default=SubtaskExecutionConstraint.OFFLOADABLE,
    )
    compute_load: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    input_data_size_mb: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    output_data_size_mb: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    task: Mapped[DagTask] = relationship(back_populates="subtasks")
    schedule_items: Mapped[list["SchedulePlanItem"]] = relationship(
        back_populates="subtask"
    )
    execution_records: Mapped[list["ExecutionRecord"]] = relationship(
        back_populates="subtask"
    )


class DagDependency(Base):
    __tablename__ = "dag_dependencies"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("dag_tasks.id"), nullable=False, index=True)
    predecessor_subtask_id: Mapped[UUID] = mapped_column(
        ForeignKey("dag_subtasks.id"),
        nullable=False,
        index=True,
    )
    successor_subtask_id: Mapped[UUID] = mapped_column(
        ForeignKey("dag_subtasks.id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task: Mapped[DagTask] = relationship(back_populates="dependencies")


class SchedulePlan(Base):
    __tablename__ = "schedule_plans"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("dag_tasks.id"), nullable=False, index=True)
    strategy_name: Mapped[SchedulerStrategyName] = mapped_column(String(64), nullable=False)
    status: Mapped[SchedulePlanStatus] = mapped_column(
        String(16),
        nullable=False,
        default=SchedulePlanStatus.GENERATED,
    )
    estimated_total_duration_ms: Mapped[int | None] = mapped_column(Integer)
    estimated_total_energy: Mapped[float | None] = mapped_column(Numeric(14, 4))
    options_json: Mapped[dict[str, object]] = mapped_column(
        "options",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    task: Mapped[DagTask] = relationship(back_populates="schedule_plans")
    items: Mapped[list["SchedulePlanItem"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class SchedulePlanItem(Base):
    __tablename__ = "schedule_plan_items"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("schedule_plans.id"),
        nullable=False,
        index=True,
    )
    subtask_id: Mapped[UUID] = mapped_column(
        ForeignKey("dag_subtasks.id"),
        nullable=False,
        index=True,
    )
    assigned_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("nodes.id"),
        nullable=False,
        index=True,
    )
    estimated_compute_duration_ms: Mapped[int | None] = mapped_column(Integer)
    estimated_transfer_duration_ms: Mapped[int | None] = mapped_column(Integer)
    estimated_energy: Mapped[float | None] = mapped_column(Numeric(14, 4))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plan: Mapped[SchedulePlan] = relationship(back_populates="items")
    subtask: Mapped[DagSubtask] = relationship(back_populates="schedule_items")
    execution_records: Mapped[list["ExecutionRecord"]] = relationship(
        back_populates="plan_item"
    )


class ExecutionRecord(Base):
    __tablename__ = "execution_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("dag_tasks.id"), nullable=False, index=True)
    subtask_id: Mapped[UUID] = mapped_column(
        ForeignKey("dag_subtasks.id"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[UUID] = mapped_column(ForeignKey("nodes.id"), nullable=False, index=True)
    plan_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("schedule_plan_items.id"),
        index=True,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    output_summary: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    task: Mapped[DagTask] = relationship(back_populates="execution_records")
    subtask: Mapped[DagSubtask] = relationship(back_populates="execution_records")
    plan_item: Mapped[SchedulePlanItem | None] = relationship(
        back_populates="execution_records"
    )
