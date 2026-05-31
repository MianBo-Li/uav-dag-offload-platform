from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.node import Node, NodeStatusRecord
from app.db.models.task import SchedulePlan
from app.domain.enums import (
    NodeStatus,
    NodeType,
    SchedulePlanStatus,
    SchedulerStrategyName,
    SubtaskExecutionConstraint,
    TaskStatus,
)
from app.schemas.task import DagTaskCreate, DependencyCreate, SubtaskCreate
from app.services.scheduling_service import SchedulingService
from app.services.task_service import TaskService


def _task_payload() -> DagTaskCreate:
    return DagTaskCreate(
        name="inspection-task-001",
        priority=1,
        subtasks=[
            SubtaskCreate(
                external_id="capture_image",
                name="Capture image",
                compute_load=80.0,
                input_data_size_mb=0.0,
                output_data_size_mb=120.0,
                execution_constraint=SubtaskExecutionConstraint.LOCAL_ONLY,
            ),
            SubtaskCreate(
                external_id="detect_target",
                name="Detect target",
                compute_load=500.0,
                input_data_size_mb=20.0,
                output_data_size_mb=10.0,
            ),
        ],
        dependencies=[
            DependencyCreate.model_validate(
                {"from": "capture_image", "to": "detect_target"}
            ),
        ],
    )


def _create_node(
    db_session: Session,
    *,
    name: str,
    node_type: NodeType,
    cpu_capacity: float,
    status: NodeStatus = NodeStatus.ONLINE,
    bandwidth_mbps: float | None = None,
) -> Node:
    node = Node(
        name=name,
        node_type=node_type,
        status=status,
        cpu_capacity=cpu_capacity,
        memory_capacity_mb=2048,
    )
    db_session.add(node)
    db_session.flush()
    db_session.refresh(node)

    record = NodeStatusRecord(
        node_id=node.id,
        cpu_usage=0.0,
        memory_usage=30.0,
        bandwidth_mbps=bandwidth_mbps,
        reported_at=datetime(2026, 5, 26, 10, 0, tzinfo=UTC),
    )
    db_session.add(record)
    db_session.flush()
    return node


def test_scheduling_service_persists_plan_and_updates_task_status(
    db_session: Session,
) -> None:
    task = TaskService(db_session).create_task(_task_payload())
    capture_subtask = next(
        subtask for subtask in task.subtasks if subtask.external_id == "capture_image"
    )
    uav = _create_node(
        db_session,
        name="UAV-001",
        node_type=NodeType.UAV,
        cpu_capacity=100.0,
    )
    _create_node(
        db_session,
        name="EDGE-001",
        node_type=NodeType.EDGE,
        cpu_capacity=1000.0,
        bandwidth_mbps=100.0,
    )

    plan = SchedulingService(db_session).generate_plan(
        task.id,
        SchedulerStrategyName.GREEDY,
    )

    assert plan.strategy_name == SchedulerStrategyName.GREEDY
    assert plan.task_id == task.id
    assert plan.status == SchedulePlanStatus.GENERATED
    assert len(plan.items) == 1
    assert plan.items[0].subtask_id == capture_subtask.id
    assert plan.items[0].assigned_node_id == uav.id

    db_session.flush()
    db_session.refresh(task)
    saved_plan = db_session.get(SchedulePlan, plan.id)
    assert saved_plan is not None
    assert task.status == TaskStatus.SCHEDULED
    assert task.scheduled_at is not None


def test_scheduling_service_rejects_rescheduling_scheduled_task(
    db_session: Session,
) -> None:
    task = TaskService(db_session).create_task(_task_payload())
    _create_node(
        db_session,
        name="UAV-001",
        node_type=NodeType.UAV,
        cpu_capacity=100.0,
    )

    service = SchedulingService(db_session)
    service.generate_plan(task.id, SchedulerStrategyName.GREEDY)

    with pytest.raises(AppError) as exc_info:
        service.generate_plan(task.id, SchedulerStrategyName.GREEDY)

    assert exc_info.value.code == "TASK_STATE_CONFLICT"
    assert exc_info.value.status_code == 409


def test_scheduling_service_rejects_unknown_strategy(db_session: Session) -> None:
    task = TaskService(db_session).create_task(_task_payload())

    with pytest.raises(AppError) as exc_info:
        SchedulingService(db_session).generate_plan(task.id, "unknown")

    assert exc_info.value.code == "SCHEDULER_STRATEGY_NOT_FOUND"
    assert exc_info.value.status_code == 400


def test_scheduling_service_requires_online_nodes(db_session: Session) -> None:
    task = TaskService(db_session).create_task(_task_payload())
    _create_node(
        db_session,
        name="UAV-001",
        node_type=NodeType.UAV,
        status=NodeStatus.OFFLINE,
        cpu_capacity=100.0,
    )

    with pytest.raises(AppError) as exc_info:
        SchedulingService(db_session).generate_plan(
            task.id,
            SchedulerStrategyName.GREEDY,
        )

    assert exc_info.value.code == "NO_AVAILABLE_NODE"
    assert exc_info.value.status_code == 409
