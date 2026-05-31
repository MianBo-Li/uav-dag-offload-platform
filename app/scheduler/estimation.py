from dataclasses import dataclass
from math import inf

from app.domain.enums import NodeType, SubtaskExecutionConstraint
from app.scheduler.base import NodeSnapshot, SchedulableSubtask


@dataclass(frozen=True)
class CandidateEstimate:
    node: NodeSnapshot
    compute_duration_ms: int
    transfer_duration_ms: int | float
    energy: float
    score: float


def estimate_candidate(
    subtask: SchedulableSubtask,
    node: NodeSnapshot,
    energy_cost_weight: float,
) -> CandidateEstimate:
    compute_duration_ms = compute_duration_ms_for(subtask, node)
    transfer_duration_ms = transfer_duration_ms_for(subtask, node)
    energy = estimate_energy(compute_duration_ms, transfer_duration_ms, node)
    score = compute_duration_ms + transfer_duration_ms + energy_cost_weight * energy
    return CandidateEstimate(
        node=node,
        compute_duration_ms=compute_duration_ms,
        transfer_duration_ms=transfer_duration_ms,
        energy=energy,
        score=score,
    )


def node_matches_constraint(
    subtask: SchedulableSubtask,
    node: NodeSnapshot,
) -> bool:
    if subtask.execution_constraint == SubtaskExecutionConstraint.LOCAL_ONLY:
        return node.node_type == NodeType.UAV
    if subtask.execution_constraint == SubtaskExecutionConstraint.EDGE_ONLY:
        return node.node_type == NodeType.EDGE
    return True


def compute_duration_ms_for(subtask: SchedulableSubtask, node: NodeSnapshot) -> int:
    usage_ratio = min(max(node.cpu_usage_percent, 0.0), 95.0) / 100
    effective_cpu_capacity = node.cpu_capacity * (1 - usage_ratio)
    seconds = subtask.compute_load / effective_cpu_capacity
    return round(seconds * 1000)


def transfer_duration_ms_for(
    subtask: SchedulableSubtask,
    node: NodeSnapshot,
) -> int | float:
    if node.node_type == NodeType.UAV or subtask.input_data_size_mb == 0:
        return 0

    if node.bandwidth_mbps is None or node.bandwidth_mbps <= 0:
        return inf

    seconds = subtask.input_data_size_mb / node.bandwidth_mbps
    return round(seconds * 1000)


def estimate_energy(
    compute_duration_ms: int,
    transfer_duration_ms: int | float,
    node: NodeSnapshot,
) -> float:
    compute_seconds = compute_duration_ms / 1000
    transfer_seconds = transfer_duration_ms / 1000
    if node.node_type == NodeType.UAV:
        return compute_seconds * 2.0
    return compute_seconds * 0.4 + transfer_seconds * 0.8


def float_option(
    options: dict[str, object] | None,
    key: str,
    *,
    default: float,
) -> float:
    if options is None or key not in options:
        return default
    value = options[key]
    if isinstance(value, int | float):
        return float(value)
    return default
