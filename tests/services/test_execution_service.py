from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.db.models.node import Node, NodeStatusRecord
from app.domain.enums import (
    ExecutionStatus,
    NodeType,
    SchedulerStrategyName,
    SubtaskExecutionConstraint,
)
from app.repositories.execution_repository import ExecutionRepository
from app.schemas.task import DagTaskCreate, SubtaskCreate
from app.services.execution_service import ExecutionService
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
        ],
    )


def _create_uav_node(db_session: Session) -> Node:
    node = Node(
        name="UAV-001",
        node_type=NodeType.UAV,
        cpu_capacity=100.0,
        memory_capacity_mb=2048,
    )
    db_session.add(node)
    db_session.flush()
    db_session.refresh(node)

    db_session.add(
        NodeStatusRecord(
            node_id=node.id,
            cpu_usage=0.0,
            memory_usage=30.0,
            reported_at=datetime(2026, 6, 8, 10, 0, tzinfo=UTC),
        )
    )
    db_session.flush()
    return node


def _start_ready_execution(db_session: Session) -> UUID:
    task = TaskService(db_session).create_task(_task_payload())
    _create_uav_node(db_session)
    plan = SchedulingService(db_session).generate_plan(
        task.id,
        SchedulerStrategyName.GREEDY,
    )
    result = ExecutionService(db_session).start_execution(task.id, plan.id)
    return result.execution_ids[0]


def test_report_result_uses_locked_execution_lookup(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_id = _start_ready_execution(db_session)
    locked_lookup_ids: list[UUID] = []
    original_get_by_id_for_update = ExecutionRepository.get_by_id_for_update

    def tracking_get_by_id_for_update(
        self: ExecutionRepository,
        lookup_id: UUID,
    ):
        locked_lookup_ids.append(lookup_id)
        return original_get_by_id_for_update(self, lookup_id)

    monkeypatch.setattr(
        ExecutionRepository,
        "get_by_id_for_update",
        tracking_get_by_id_for_update,
    )

    result = ExecutionService(db_session).report_result(
        execution_id,
        ExecutionStatus.SUCCESS,
        duration_ms=250,
        output_summary="image captured",
    )

    assert locked_lookup_ids == [execution_id]
    assert result.accepted is True
