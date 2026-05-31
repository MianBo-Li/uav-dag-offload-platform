from math import isfinite
from random import Random

from app.domain.enums import NodeStatus, SchedulerStrategyName
from app.scheduler.base import (
    NoAvailableNodeError,
    NoSchedulableSubtaskError,
    NodeSnapshot,
    SchedulePlan,
    SchedulePlanItem,
    SchedulableSubtask,
)
from app.scheduler.estimation import estimate_candidate, float_option, node_matches_constraint


class RandomOffloadScheduler:
    name = SchedulerStrategyName.RANDOM_OFFLOAD

    def generate_plan(
        self,
        subtasks: list[SchedulableSubtask],
        nodes: list[NodeSnapshot],
        options: dict[str, object] | None = None,
    ) -> SchedulePlan:
        if not subtasks:
            raise NoSchedulableSubtaskError("No schedulable subtasks")

        online_nodes = [
            node for node in nodes if node.status == NodeStatus.ONLINE and node.cpu_capacity > 0
        ]
        if not online_nodes:
            raise NoAvailableNodeError("No online nodes are available for scheduling")

        energy_cost_weight = float_option(options, "energy_cost_weight", default=0.2)
        random = Random(_seed_option(options))
        items: list[SchedulePlanItem] = []

        for subtask in subtasks:
            candidates = [
                estimate_candidate(subtask, node, energy_cost_weight)
                for node in online_nodes
                if node_matches_constraint(subtask, node)
            ]
            candidates = [candidate for candidate in candidates if isfinite(candidate.score)]
            if not candidates:
                raise NoAvailableNodeError(
                    "No available node can execute subtask "
                    f"{subtask.external_id} with constraint "
                    f"{subtask.execution_constraint}"
                )

            candidate = random.choice(candidates)
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
                    decision_reason="selected by random-offload strategy",
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


def _seed_option(options: dict[str, object] | None) -> int | None:
    if options is None or "seed" not in options:
        return None
    seed = options["seed"]
    if isinstance(seed, int):
        return seed
    return None
