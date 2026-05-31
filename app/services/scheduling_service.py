from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.task import SchedulePlan, SchedulePlanItem
from app.domain.enums import (
    NodeStatus,
    NodeType,
    SchedulePlanStatus,
    SchedulerStrategyName,
    SubtaskStatus,
    TaskStatus,
)
from app.domain.state_machine import ensure_transition_allowed
from app.repositories.node_repository import NodeRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.scheduler.base import (
    SchedulePlan as GeneratedSchedulePlan,
    NoAvailableNodeError,
    NoSchedulableSubtaskError,
    NodeSnapshot,
    SchedulerStrategy,
    SchedulableSubtask,
)
from app.scheduler.greedy import GreedyScheduler
from app.scheduler.local_only import LocalOnlyScheduler
from app.scheduler.random_offload import RandomOffloadScheduler
from app.services.task_service import TaskService


@dataclass(frozen=True)
class ScheduleComparisonItem:
    strategy_name: SchedulerStrategyName
    feasible: bool
    failure_code: str | None
    failure_reason: str | None
    schedulable_subtask_count: int
    estimated_total_duration_ms: int | None
    estimated_total_energy: float | None
    local_assignment_count: int
    edge_assignment_count: int


class SchedulingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.task_service = TaskService(db)
        self.node_repository = NodeRepository(db)
        self.schedule_repository = ScheduleRepository(db)
        self.strategies: dict[SchedulerStrategyName, SchedulerStrategy] = {
            SchedulerStrategyName.LOCAL_ONLY: LocalOnlyScheduler(),
            SchedulerStrategyName.RANDOM_OFFLOAD: RandomOffloadScheduler(),
            SchedulerStrategyName.GREEDY: GreedyScheduler(),
        }

    def generate_plan(
        self,
        task_id: UUID,
        strategy_name: SchedulerStrategyName | str,
        options: dict[str, object] | None = None,
    ) -> SchedulePlan:
        strategy = self._get_strategy(strategy_name)
        task = self.task_service.get_task(task_id)
        self._ensure_task_can_schedule(task.status, task_id)

        subtasks = self._build_schedulable_subtasks(task)
        node_snapshots = self._load_node_snapshots()

        try:
            generated_plan = strategy.generate_plan(subtasks, node_snapshots, options)
        except NoSchedulableSubtaskError as exc:
            raise AppError(
                code="NO_SCHEDULABLE_SUBTASK",
                message=str(exc),
                status_code=409,
                details={"task_id": str(task_id)},
            ) from exc
        except NoAvailableNodeError as exc:
            raise AppError(
                code="NO_AVAILABLE_NODE",
                message=str(exc),
                status_code=409,
                details={"task_id": str(task_id)},
            ) from exc

        return self._persist_plan(task, generated_plan, options)

    def compare_strategies(self, task_id: UUID) -> list[ScheduleComparisonItem]:
        task = self.task_service.get_task(task_id)
        subtasks = self._build_schedulable_subtasks(task)
        node_snapshots = self._load_node_snapshots()
        items: list[ScheduleComparisonItem] = []

        for strategy_name, strategy in self.strategies.items():
            try:
                generated_plan = strategy.generate_plan(
                    subtasks,
                    node_snapshots,
                    _comparison_options(strategy_name),
                )
            except NoSchedulableSubtaskError as exc:
                items.append(
                    ScheduleComparisonItem(
                        strategy_name=strategy_name,
                        feasible=False,
                        failure_code="NO_SCHEDULABLE_SUBTASK",
                        failure_reason=str(exc),
                        schedulable_subtask_count=len(subtasks),
                        estimated_total_duration_ms=None,
                        estimated_total_energy=None,
                        local_assignment_count=0,
                        edge_assignment_count=0,
                    )
                )
            except NoAvailableNodeError as exc:
                items.append(
                    ScheduleComparisonItem(
                        strategy_name=strategy_name,
                        feasible=False,
                        failure_code="NO_AVAILABLE_NODE",
                        failure_reason=str(exc),
                        schedulable_subtask_count=len(subtasks),
                        estimated_total_duration_ms=None,
                        estimated_total_energy=None,
                        local_assignment_count=0,
                        edge_assignment_count=0,
                    )
                )
            else:
                items.append(
                    ScheduleComparisonItem(
                        strategy_name=strategy_name,
                        feasible=True,
                        failure_code=None,
                        failure_reason=None,
                        schedulable_subtask_count=len(subtasks),
                        estimated_total_duration_ms=(
                            generated_plan.estimated_total_duration_ms
                        ),
                        estimated_total_energy=generated_plan.estimated_total_energy,
                        local_assignment_count=sum(
                            item.assigned_node_type == NodeType.UAV
                            for item in generated_plan.items
                        ),
                        edge_assignment_count=sum(
                            item.assigned_node_type == NodeType.EDGE
                            for item in generated_plan.items
                        ),
                    )
                )

        return items

    def get_plan(self, plan_id: UUID) -> SchedulePlan:
        plan = self.schedule_repository.get_by_id(plan_id)
        if plan is None:
            raise AppError(
                code="SCHEDULE_PLAN_NOT_FOUND",
                message="Schedule plan not found",
                status_code=404,
                details={"schedule_plan_id": str(plan_id)},
            )
        return plan

    def list_task_plans(
        self,
        task_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[SchedulePlan], int]:
        self.task_service.get_task(task_id)
        return self.schedule_repository.list_by_task(task_id, page, page_size)

    @staticmethod
    def _build_schedulable_subtasks(task) -> list[SchedulableSubtask]:
        return [
            SchedulableSubtask(
                id=subtask.id,
                external_id=subtask.external_id,
                compute_load=float(subtask.compute_load),
                input_data_size_mb=float(subtask.input_data_size_mb),
                output_data_size_mb=float(subtask.output_data_size_mb),
                execution_constraint=subtask.execution_constraint,
            )
            for subtask in task.subtasks
            if subtask.status == SubtaskStatus.READY
        ]

    def _get_strategy(
        self,
        strategy_name: SchedulerStrategyName | str,
    ) -> SchedulerStrategy:
        try:
            normalized_name = SchedulerStrategyName(strategy_name)
        except ValueError as exc:
            raise AppError(
                code="SCHEDULER_STRATEGY_NOT_FOUND",
                message="Scheduler strategy not found",
                status_code=400,
                details={"strategy_name": str(strategy_name)},
            ) from exc

        strategy = self.strategies.get(normalized_name)
        if strategy is None:
            raise AppError(
                code="SCHEDULER_STRATEGY_NOT_FOUND",
                message="Scheduler strategy not found",
                status_code=400,
                details={"strategy_name": str(strategy_name)},
            )
        return strategy

    def _persist_plan(
        self,
        task,
        generated_plan: GeneratedSchedulePlan,
        options: dict[str, object] | None,
    ) -> SchedulePlan:
        plan = SchedulePlan(
            task_id=task.id,
            strategy_name=generated_plan.strategy_name,
            status=SchedulePlanStatus.GENERATED,
            estimated_total_duration_ms=generated_plan.estimated_total_duration_ms,
            estimated_total_energy=generated_plan.estimated_total_energy,
            options_json=options or {},
        )
        plan.items = [
            SchedulePlanItem(
                subtask_id=item.subtask_id,
                assigned_node_id=item.assigned_node_id,
                estimated_compute_duration_ms=item.estimated_compute_duration_ms,
                estimated_transfer_duration_ms=int(item.estimated_transfer_duration_ms),
                estimated_energy=item.estimated_energy,
                decision_reason=item.decision_reason,
            )
            for item in generated_plan.items
        ]

        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.SCHEDULED
            task.scheduled_at = datetime.now(UTC)

        saved_plan = self.schedule_repository.create(plan)
        self.db.flush()
        self.db.refresh(task)
        return saved_plan

    @staticmethod
    def _ensure_task_can_schedule(status: TaskStatus, task_id: UUID) -> None:
        if status == TaskStatus.RUNNING:
            return

        try:
            ensure_transition_allowed(status, TaskStatus.SCHEDULED)
        except ValueError as exc:
            raise AppError(
                code="TASK_STATE_CONFLICT",
                message=str(exc),
                status_code=409,
                details={
                    "task_id": str(task_id),
                    "current_status": status,
                    "target_status": TaskStatus.SCHEDULED,
                },
            ) from exc

    def _load_node_snapshots(self) -> list[NodeSnapshot]:
        nodes = self.node_repository.list_by_status(NodeStatus.ONLINE)
        snapshots: list[NodeSnapshot] = []

        for node in nodes:
            latest_record = self.node_repository.get_latest_status_record(node.id)
            snapshots.append(
                NodeSnapshot(
                    id=node.id,
                    name=node.name,
                    node_type=node.node_type,
                    status=node.status,
                    cpu_capacity=float(node.cpu_capacity),
                    memory_capacity_mb=node.memory_capacity_mb,
                    cpu_usage_percent=(
                        float(latest_record.cpu_usage) if latest_record else 0.0
                    ),
                    memory_usage_percent=(
                        float(latest_record.memory_usage) if latest_record else 0.0
                    ),
                    battery_level=(
                        float(latest_record.battery_level)
                        if latest_record and latest_record.battery_level is not None
                        else None
                    ),
                    bandwidth_mbps=(
                        float(latest_record.bandwidth_mbps)
                        if latest_record and latest_record.bandwidth_mbps is not None
                        else None
                    ),
                    current_load=latest_record.current_load if latest_record else None,
                    queue_length=latest_record.queue_length if latest_record else None,
                )
            )

        return snapshots


def _comparison_options(strategy_name: SchedulerStrategyName) -> dict[str, object]:
    if strategy_name == SchedulerStrategyName.RANDOM_OFFLOAD:
        return {"seed": 0}
    return {}
