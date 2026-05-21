from collections import defaultdict, deque


def validate_dag(subtask_ids: list[str], dependencies: list[tuple[str, str]]) -> None:
    if not subtask_ids:
        raise ValueError("DAG must contain at least one subtask")

    if len(subtask_ids) != len(set(subtask_ids)):
        raise ValueError("Subtask IDs must be unique")

    subtask_id_set = set(subtask_ids)
    for predecessor, successor in dependencies:
        if predecessor not in subtask_id_set or successor not in subtask_id_set:
            raise ValueError("Dependency references an unknown subtask")
        if predecessor == successor:
            raise ValueError("Subtask cannot depend on itself")

    incoming_count: dict[str, int] = {subtask_id: 0 for subtask_id in subtask_ids}
    graph: dict[str, list[str]] = defaultdict(list)

    for predecessor, successor in dependencies:
        graph[predecessor].append(successor)
        incoming_count[successor] += 1

    queue = deque(
        subtask_id for subtask_id, count in incoming_count.items() if count == 0
    )
    visited_count = 0

    while queue:
        current = queue.popleft()
        visited_count += 1
        for successor in graph[current]:
            incoming_count[successor] -= 1
            if incoming_count[successor] == 0:
                queue.append(successor)

    if visited_count != len(subtask_ids):
        raise ValueError("DAG contains a cycle")
