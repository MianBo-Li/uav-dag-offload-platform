from uuid import UUID

import pytest

from app.domain.enums import (
    NodeStatus,
    NodeType,
    SchedulerStrategyName,
    SubtaskExecutionConstraint,
)
from app.scheduler.base import (
    NoAvailableNodeError,
    NoSchedulableSubtaskError,
    NodeSnapshot,
    SchedulableSubtask,
)
from app.scheduler.greedy import GreedyScheduler


def _subtask(
    *,
    compute_load: float = 100.0,
    input_data_size_mb: float = 0.0,
    execution_constraint: SubtaskExecutionConstraint = (
        SubtaskExecutionConstraint.OFFLOADABLE
    ),
) -> SchedulableSubtask:
    return SchedulableSubtask(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        external_id="detect_target",
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


def test_greedy_scheduler_prefers_edge_for_compute_heavy_subtask() -> None:
    subtask = _subtask(compute_load=500.0, input_data_size_mb=20.0)
    uav = _node(
        id_="00000000-0000-0000-0000-000000000101",
        name="UAV-001",
        node_type=NodeType.UAV,
        cpu_capacity=100.0,
    )
    edge = _node(
        id_="00000000-0000-0000-0000-000000000201",
        name="EDGE-001",
        node_type=NodeType.EDGE,
        cpu_capacity=1000.0,
        bandwidth_mbps=100.0,
    )

    plan = GreedyScheduler().generate_plan([subtask], [uav, edge])

    assert plan.strategy_name == SchedulerStrategyName.GREEDY
    assert len(plan.items) == 1
    item = plan.items[0]
    assert item.subtask_id == subtask.id
    assert item.assigned_node_id == edge.id
    assert item.assigned_node_name == "EDGE-001"
    assert item.estimated_compute_duration_ms == 500
    assert item.estimated_transfer_duration_ms == 200
    assert plan.estimated_total_duration_ms == 700


def test_greedy_scheduler_keeps_subtask_on_uav_when_transfer_is_expensive() -> None:
    subtask = _subtask(compute_load=50.0, input_data_size_mb=1000.0)
    uav = _node(
        id_="00000000-0000-0000-0000-000000000101",
        name="UAV-001",
        node_type=NodeType.UAV,
        cpu_capacity=100.0,
    )
    edge = _node(
        id_="00000000-0000-0000-0000-000000000201",
        name="EDGE-001",
        node_type=NodeType.EDGE,
        cpu_capacity=1000.0,
        bandwidth_mbps=10.0,
    )

    plan = GreedyScheduler().generate_plan([subtask], [uav, edge])

    assert plan.items[0].assigned_node_id == uav.id
    assert plan.items[0].estimated_transfer_duration_ms == 0


def test_greedy_scheduler_respects_local_only_constraint() -> None:
    subtask = _subtask(
        compute_load=80.0,
        input_data_size_mb=0.0,
        execution_constraint=SubtaskExecutionConstraint.LOCAL_ONLY,
    )
    uav = _node(
        id_="00000000-0000-0000-0000-000000000101",
        name="UAV-001",
        node_type=NodeType.UAV,
        cpu_capacity=100.0,
    )
    edge = _node(
        id_="00000000-0000-0000-0000-000000000201",
        name="EDGE-001",
        node_type=NodeType.EDGE,
        cpu_capacity=1000.0,
        bandwidth_mbps=100.0,
    )

    plan = GreedyScheduler().generate_plan([subtask], [uav, edge])

    assert plan.items[0].assigned_node_id == uav.id


def test_greedy_scheduler_ignores_offline_nodes() -> None:
    subtask = _subtask(compute_load=500.0, input_data_size_mb=20.0)
    uav = _node(
        id_="00000000-0000-0000-0000-000000000101",
        name="UAV-001",
        node_type=NodeType.UAV,
        cpu_capacity=100.0,
    )
    offline_edge = _node(
        id_="00000000-0000-0000-0000-000000000201",
        name="EDGE-001",
        node_type=NodeType.EDGE,
        cpu_capacity=1000.0,
        status=NodeStatus.OFFLINE,
        bandwidth_mbps=100.0,
    )

    plan = GreedyScheduler().generate_plan([subtask], [uav, offline_edge])

    assert plan.items[0].assigned_node_id == uav.id


def test_greedy_scheduler_rejects_empty_subtask_list() -> None:
    uav = _node(
        id_="00000000-0000-0000-0000-000000000101",
        name="UAV-001",
        node_type=NodeType.UAV,
        cpu_capacity=100.0,
    )

    with pytest.raises(NoSchedulableSubtaskError, match="No schedulable subtasks"):
        GreedyScheduler().generate_plan([], [uav])


def test_greedy_scheduler_rejects_when_no_online_nodes() -> None:
    subtask = _subtask()
    offline_uav = _node(
        id_="00000000-0000-0000-0000-000000000101",
        name="UAV-001",
        node_type=NodeType.UAV,
        status=NodeStatus.OFFLINE,
        cpu_capacity=100.0,
    )

    with pytest.raises(NoAvailableNodeError, match="No online nodes"):
        GreedyScheduler().generate_plan([subtask], [offline_uav])
