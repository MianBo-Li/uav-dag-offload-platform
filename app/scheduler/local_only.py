from math import isfinite

from app.domain.enums import NodeStatus, NodeType, SchedulerStrategyName
from app.scheduler.base import (
    NoAvailableNodeError,
    NoSchedulableSubtaskError,
    NodeSnapshot,
    SchedulePlan,
    SchedulePlanItem,
    SchedulableSubtask,
)
from app.scheduler.estimation import estimate_candidate, float_option, node_matches_constraint


class LocalOnlyScheduler:
    name = SchedulerStrategyName.LOCAL_ONLY

    def generate_plan(
        self,
        subtasks: list[SchedulableSubtask],
        nodes: list[NodeSnapshot],
        options: dict[str, object] | None = None,
    ) -> SchedulePlan:
        if not subtasks:
            raise NoSchedulableSubtaskError("No schedulable subtasks")

        online_uavs = [
            node
            for node in nodes
            if node.status == NodeStatus.ONLINE
            and node.node_type == NodeType.UAV
            and node.cpu_capacity > 0
        ]
        if not online_uavs:
            raise NoAvailableNodeError("No online UAV nodes are available for scheduling")

        energy_cost_weight = float_option(options, "energy_cost_weight", default=0.2)
        items: list[SchedulePlanItem] = []

        for subtask in subtasks:
            candidates = [
                estimate_candidate(subtask, node, energy_cost_weight)
                for node in online_uavs
                if node_matches_constraint(subtask, node)
            ]
            candidates = [candidate for candidate in candidates if isfinite(candidate.score)]
            if not candidates:
                raise NoAvailableNodeError(
                    "No local UAV node can execute subtask "
                    f"{subtask.external_id} with constraint "
                    f"{subtask.execution_constraint}"
                )

            candidate = min(
                candidates,
                key=lambda item: (
                    item.compute_duration_ms,
                    item.node.queue_length or 0,
                    item.node.current_load or 0,
                    item.node.name,
                ),
            )
            items.append(
                SchedulePlanItem(
                    subtask_id=subtask.id,
                    subtask_external_id=subtask.external_id,
                    assigned_node_id=candidate.node.id,
                    assigned_node_name=candidate.node.name,
                    assigned_node_type=candidate.node.node_type,
                    estimated_compute_duration_ms=candidate.compute_duration_ms,
                    estimated_transfer_duration_ms=int(candidate.transfer_duration_ms),
                    estimated_energy=round(candidate.energy, 4),
                    decision_reason="selected by local-only strategy",
                )
            )

        return SchedulePlan(
            strategy_name=self.name,
            items=items,
            estimated_total_duration_ms=sum(
                item.estimated_compute_duration_ms + item.estimated_transfer_duration_ms
                for item in items
            ),
            estimated_total_energy=round(sum(item.estimated_energy for item in items), 4),
        )
