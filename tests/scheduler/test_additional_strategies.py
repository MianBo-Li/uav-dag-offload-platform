from uuid import UUID

import pytest

from app.domain.enums import (
    NodeStatus,
    NodeType,
    SchedulerStrategyName,
    SubtaskExecutionConstraint,
)
from app.scheduler.base import NoAvailableNodeError, NodeSnapshot, SchedulableSubtask
from app.scheduler.local_only import LocalOnlyScheduler
from app.scheduler.random_offload import RandomOffloadScheduler


def _subtask(
    *,
    id_: str = "00000000-0000-0000-0000-000000000001",
    external_id: str = "detect_target",
    compute_load: float = 100.0,
    input_data_size_mb: float = 20.0,
    execution_constraint: SubtaskExecutionConstraint = (
        SubtaskExecutionConstraint.OFFLOADABLE
    ),
) -> SchedulableSubtask:
    return SchedulableSubtask(
        id=UUID(id_),
        external_id=external_id,
        compute_load=compute_load,
        input_data_size_mb=input_data_size_mb,
        output_data_size_mb=10.0,
        execution_constraint=execution_constraint,
    )


def _node(
    *,
    id_: str,
    name: str,
    node_type: NodeType,
    cpu_capacity: float,
    status: NodeStatus = NodeStatus.ONLINE,
    bandwidth_mbps: float | None = None,
) -> NodeSnapshot:
    return NodeSnapshot(
        id=UUID(id_),
        name=name,
        node_type=node_type,
        status=status,
        cpu_capacity=cpu_capacity,
        memory_capacity_mb=2048,
        bandwidth_mbps=bandwidth_mbps,
    )


def _uav() -> NodeSnapshot:
    return _node(
        id_="00000000-0000-0000-0000-000000000101",
        name="UAV-001",
        node_type=NodeType.UAV,
        cpu_capacity=100.0,
    )


def _edge() -> NodeSnapshot:
    return _node(
        id_="00000000-0000-0000-0000-000000000201",
        name="EDGE-001",
        node_type=NodeType.EDGE,
        cpu_capacity=1000.0,
        bandwidth_mbps=100.0,
    )


def test_local_only_scheduler_assigns_offloadable_subtask_to_uav() -> None:
    plan = LocalOnlyScheduler().generate_plan([_subtask()], [_uav(), _edge()])

    assert plan.strategy_name == SchedulerStrategyName.LOCAL_ONLY
    assert plan.items[0].assigned_node_type == NodeType.UAV
    assert plan.items[0].estimated_transfer_duration_ms == 0


def test_local_only_scheduler_rejects_edge_only_subtask() -> None:
    subtask = _subtask(execution_constraint=SubtaskExecutionConstraint.EDGE_ONLY)

    with pytest.raises(NoAvailableNodeError, match="No local UAV node"):
        LocalOnlyScheduler().generate_plan([subtask], [_uav(), _edge()])


def test_random_offload_scheduler_is_repeatable_with_seed() -> None:
    subtasks = [
        _subtask(
            id_="00000000-0000-0000-0000-000000000001",
            external_id="task-a",
        ),
        _subtask(
            id_="00000000-0000-0000-0000-000000000002",
            external_id="task-b",
        ),
    ]
    nodes = [_uav(), _edge()]

    first_plan = RandomOffloadScheduler().generate_plan(
        subtasks,
        nodes,
        {"seed": 42},
    )
    second_plan = RandomOffloadScheduler().generate_plan(
        subtasks,
        nodes,
        {"seed": 42},
    )

    assert first_plan.strategy_name == SchedulerStrategyName.RANDOM_OFFLOAD
    assert [item.assigned_node_id for item in first_plan.items] == [
        item.assigned_node_id for item in second_plan.items
    ]


def test_random_offload_scheduler_respects_local_only_constraint() -> None:
    subtask = _subtask(execution_constraint=SubtaskExecutionConstraint.LOCAL_ONLY)

    plan = RandomOffloadScheduler().generate_plan(
        [subtask],
        [_uav(), _edge()],
        {"seed": 42},
    )

    assert plan.items[0].assigned_node_type == NodeType.UAV
