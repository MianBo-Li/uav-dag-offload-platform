from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.enums import (
    NodeStatus,
    NodeType,
    SchedulerStrategyName,
    SubtaskExecutionConstraint,
)


@dataclass(frozen=True)
class SchedulableSubtask:
    id: UUID
    external_id: str
    compute_load: float
    input_data_size_mb: float
    output_data_size_mb: float
    execution_constraint: SubtaskExecutionConstraint = (
        SubtaskExecutionConstraint.OFFLOADABLE
    )


@dataclass(frozen=True)
class NodeSnapshot:
    id: UUID
    name: str
    node_type: NodeType
    status: NodeStatus
    cpu_capacity: float
    memory_capacity_mb: int
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    battery_level: float | None = None
    bandwidth_mbps: float | None = None
    current_load: int | None = None
    queue_length: int | None = None


@dataclass(frozen=True)
class SchedulePlanItem:
    subtask_id: UUID
    subtask_external_id: str
    assigned_node_id: UUID
    assigned_node_name: str
    assigned_node_type: NodeType
    estimated_compute_duration_ms: int
    estimated_transfer_duration_ms: int
    estimated_energy: float
    decision_reason: str


@dataclass(frozen=True)
class SchedulePlan:
    strategy_name: SchedulerStrategyName
    items: list[SchedulePlanItem]
    estimated_total_duration_ms: int
    estimated_total_energy: float


class SchedulingError(Exception):
    """Base error for scheduler strategy failures."""


class NoSchedulableSubtaskError(SchedulingError):
    """Raised when a strategy receives no subtasks to schedule."""


class NoAvailableNodeError(SchedulingError):
    """Raised when no node can be selected for a subtask."""


class SchedulerStrategy(Protocol):
    name: SchedulerStrategyName

    def generate_plan(
        self,
        subtasks: list[SchedulableSubtask],
        nodes: list[NodeSnapshot],
        options: dict[str, object] | None = None,
    ) -> SchedulePlan:
        ...
