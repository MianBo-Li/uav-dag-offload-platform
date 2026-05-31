from math import isfinite

from app.domain.enums import (
    NodeStatus,
    SchedulerStrategyName,
)
from app.scheduler.base import (
    NoAvailableNodeError,
    NoSchedulableSubtaskError,
    NodeSnapshot,
    SchedulePlan,
    SchedulePlanItem,
    SchedulableSubtask,
)
from app.scheduler.estimation import (
    CandidateEstimate,
    estimate_candidate,
    float_option,
    node_matches_constraint,
)


class GreedyScheduler:
    name = SchedulerStrategyName.GREEDY

    def generate_plan(
        self,
        subtasks: list[SchedulableSubtask],
        nodes: list[NodeSnapshot],
        options: dict[str, object] | None = None,
    ) -> SchedulePlan:
        if not subtasks:
            raise NoSchedulableSubtaskError("No schedulable subtasks")

        online_nodes = [node for node in nodes if node.status == NodeStatus.ONLINE]
        if not online_nodes:
            raise NoAvailableNodeError("No online nodes are available for scheduling")

        energy_cost_weight = float_option(options, "energy_cost_weight", default=0.2)
        items: list[SchedulePlanItem] = []

        for subtask in subtasks:
            candidate = self._select_best_candidate(
                subtask,
                online_nodes,
                energy_cost_weight,
            )
            items.append(
                SchedulePlanItem(
                    subtask_id=subtask.id,
                    subtask_external_id=subtask.external_id,
                    assigned_node_id=candidate.node.id,
                    assigned_node_name=candidate.node.name,
                    assigned_node_type=candidate.node.node_type,
                    estimated_compute_duration_ms=candidate.compute_duration_ms,
                    estimated_transfer_duration_ms=candidate.transfer_duration_ms,
                    estimated_energy=round(candidate.energy, 4),
                    decision_reason=(
                        "selected by lowest estimated cost "
                        f"(compute={candidate.compute_duration_ms}ms, "
                        f"transfer={candidate.transfer_duration_ms}ms)"
                    ),
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

    def _select_best_candidate(
        self,
        subtask: SchedulableSubtask,
        nodes: list[NodeSnapshot],
        energy_cost_weight: float,
    ) -> CandidateEstimate:
        candidates = [
            estimate_candidate(subtask, node, energy_cost_weight)
            for node in nodes
            if node.cpu_capacity > 0 and node_matches_constraint(subtask, node)
        ]
        candidates = [candidate for candidate in candidates if isfinite(candidate.score)]

        if not candidates:
            raise NoAvailableNodeError(
                "No available node can execute subtask "
                f"{subtask.external_id} with constraint "
                f"{subtask.execution_constraint}"
            )

        return min(
            candidates,
            key=lambda candidate: (
                candidate.score,
                candidate.node.queue_length or 0,
                candidate.node.current_load or 0,
                candidate.node.name,
            ),
        )
