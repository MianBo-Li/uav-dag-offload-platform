from datetime import UTC, datetime

from fastapi.testclient import TestClient


def _valid_task_payload() -> dict[str, object]:
    return {
        "name": "inspection-task-001",
        "priority": 1,
        "deadline_at": datetime(2026, 5, 21, 18, 0, tzinfo=UTC).isoformat(),
        "subtasks": [
            {
                "external_id": "capture_image",
                "name": "Capture image",
                "compute_load": 80.0,
                "input_data_size_mb": 0.0,
                "output_data_size_mb": 120.0,
                "max_retries": 1,
            },
            {
                "external_id": "detect_target",
                "name": "Detect target",
                "compute_load": 300.0,
                "input_data_size_mb": 120.0,
                "output_data_size_mb": 10.0,
                "max_retries": 1,
            },
            {
                "external_id": "upload_report",
                "name": "Upload report",
                "compute_load": 40.0,
                "input_data_size_mb": 10.0,
                "output_data_size_mb": 2.0,
                "max_retries": 1,
            },
        ],
        "dependencies": [
            {"from": "capture_image", "to": "detect_target"},
            {"from": "detect_target", "to": "upload_report"},
        ],
        "metadata": {"mission": "road-inspection"},
    }


def _create_ready_nodes(client: TestClient) -> tuple[str, str]:
    uav_response = client.post(
        "/api/v1/nodes",
        json={
            "name": "UAV-001",
            "node_type": "UAV",
            "cpu_capacity": 100.0,
            "memory_capacity_mb": 2048,
        },
    )
    edge_response = client.post(
        "/api/v1/nodes",
        json={
            "name": "EDGE-001",
            "node_type": "EDGE",
            "cpu_capacity": 1000.0,
            "memory_capacity_mb": 16384,
        },
    )
    uav_id = uav_response.json()["id"]
    edge_id = edge_response.json()["id"]
    reported_at = datetime(2026, 5, 21, 12, 0, tzinfo=UTC).isoformat()

    for node_id, bandwidth_mbps in ((uav_id, None), (edge_id, 100.0)):
        client.post(
            f"/api/v1/nodes/{node_id}/status",
            json={
                "cpu_usage": 0.0,
                "memory_usage": 30.0,
                "bandwidth_mbps": bandwidth_mbps,
                "reported_at": reported_at,
            },
        )

    return uav_id, edge_id


def _local_capture_task_payload() -> dict[str, object]:
    payload = _valid_task_payload()
    subtasks = payload["subtasks"]
    assert isinstance(subtasks, list)
    capture_subtask = subtasks[0]
    assert isinstance(capture_subtask, dict)
    capture_subtask["execution_constraint"] = "LOCAL_ONLY"
    return payload


def _non_retryable_local_capture_task_payload() -> dict[str, object]:
    payload = _local_capture_task_payload()
    subtasks = payload["subtasks"]
    assert isinstance(subtasks, list)
    capture_subtask = subtasks[0]
    assert isinstance(capture_subtask, dict)
    capture_subtask["max_retries"] = 0
    return payload


def test_create_task_accepts_valid_dag(client: TestClient) -> None:
    response = client.post("/api/v1/tasks", json=_valid_task_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "inspection-task-001"
    assert body["status"] == "PENDING"
    assert body["priority"] == 1
    assert body["subtask_count"] == 3
    assert body["dependency_count"] == 2
    assert body["deadline_at"] == "2026-05-21T18:00:00Z"
    assert body["created_at"] is not None


def test_get_task_returns_subtasks_and_dependencies(client: TestClient) -> None:
    create_response = client.post("/api/v1/tasks", json=_valid_task_payload())
    task_id = create_response.json()["id"]

    response = client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == task_id
    assert body["name"] == "inspection-task-001"
    assert body["status"] == "PENDING"
    assert body["priority"] == 1
    assert body["deadline_at"] == "2026-05-21T18:00:00Z"
    assert body["created_at"] is not None
    assert body["updated_at"] is not None

    subtask_statuses = {
        subtask["external_id"]: subtask["status"] for subtask in body["subtasks"]
    }
    assert subtask_statuses == {
        "capture_image": "READY",
        "detect_target": "WAITING",
        "upload_report": "WAITING",
    }

    dependencies = {
        (dependency["from"], dependency["to"]) for dependency in body["dependencies"]
    }
    assert dependencies == {
        ("capture_image", "detect_target"),
        ("detect_target", "upload_report"),
    }


def test_list_tasks_rejects_invalid_status_filter(client: TestClient) -> None:
    response = client.get("/api/v1/tasks?status=BAD_STATUS")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_list_tasks_rejects_invalid_pagination(client: TestClient) -> None:
    for query in ("page=0", "page_size=101"):
        response = client.get(f"/api/v1/tasks?{query}")

        assert response.status_code == 422
        assert "detail" in response.json()


def test_list_task_subtasks_returns_all_subtasks(client: TestClient) -> None:
    create_response = client.post("/api/v1/tasks", json=_valid_task_payload())
    task_id = create_response.json()["id"]

    response = client.get(f"/api/v1/tasks/{task_id}/subtasks")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert {item["external_id"] for item in body["items"]} == {
        "capture_image",
        "detect_target",
        "upload_report",
    }
    assert all(item["retry_count"] == 0 for item in body["items"])


def test_list_task_subtasks_filters_by_status(client: TestClient) -> None:
    create_response = client.post("/api/v1/tasks", json=_valid_task_payload())
    task_id = create_response.json()["id"]

    response = client.get(f"/api/v1/tasks/{task_id}/subtasks?status=READY")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["external_id"] == "capture_image"
    assert body["items"][0]["status"] == "READY"


def test_list_task_subtasks_rejects_invalid_status_filter(client: TestClient) -> None:
    create_response = client.post("/api/v1/tasks", json=_valid_task_payload())
    task_id = create_response.json()["id"]

    response = client.get(f"/api/v1/tasks/{task_id}/subtasks?status=BAD_STATUS")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_list_task_subtasks_rejects_invalid_pagination(client: TestClient) -> None:
    create_response = client.post("/api/v1/tasks", json=_valid_task_payload())
    task_id = create_response.json()["id"]

    for query in ("page=0", "page_size=101"):
        response = client.get(f"/api/v1/tasks/{task_id}/subtasks?{query}")

        assert response.status_code == 422
        assert "detail" in response.json()


def test_list_subtasks_for_unknown_task_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000001/subtasks"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_cancel_task_marks_pending_task_canceled(client: TestClient) -> None:
    create_response = client.post("/api/v1/tasks", json=_valid_task_payload())
    task_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/tasks/{task_id}/cancel",
        json={"reason": "user canceled the mission"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["status"] == "CANCELED"
    assert body["reason"] == "user canceled the mission"
    assert body["updated_at"] is not None

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.json()["status"] == "CANCELED"


def test_cancel_task_rejects_already_canceled_task(client: TestClient) -> None:
    create_response = client.post("/api/v1/tasks", json=_valid_task_payload())
    task_id = create_response.json()["id"]
    assert client.post(f"/api/v1/tasks/{task_id}/cancel", json={}).status_code == 200

    response = client.post(f"/api/v1/tasks/{task_id}/cancel", json={})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_STATE_CONFLICT"


def test_cancel_unknown_task_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000001/cancel",
        json={"reason": "no longer needed"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_get_task_rejects_invalid_uuid(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/not-a-uuid")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_cancel_task_rejects_invalid_uuid(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks/not-a-uuid/cancel",
        json={"reason": "invalid id"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_schedule_task_creates_plan_and_marks_task_scheduled(
    client: TestClient,
) -> None:
    uav_id, _ = _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["task_id"] == task_id
    assert body["strategy_name"] == "greedy"
    assert body["status"] == "GENERATED"
    assert body["estimated_total_duration_ms"] is not None
    assert len(body["items"]) == 1
    assert body["items"][0]["assigned_node_id"] == uav_id
    assert body["items"][0]["estimated_compute_duration_ms"] is not None

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.json()["status"] == "SCHEDULED"


def test_schedule_task_rejects_repeated_scheduling(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    assert (
        client.post(
            f"/api/v1/tasks/{task_id}/schedule",
            json={"strategy_name": "greedy"},
        ).status_code
        == 201
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_STATE_CONFLICT"


def test_schedule_task_rejects_unknown_strategy(client: TestClient) -> None:
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "unknown"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SCHEDULER_STRATEGY_NOT_FOUND"


def test_schedule_task_accepts_local_only_strategy(client: TestClient) -> None:
    uav_id, _ = _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_valid_task_payload())
    task_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "local_only"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["strategy_name"] == "local_only"
    assert len(body["items"]) == 1
    assert body["items"][0]["assigned_node_id"] == uav_id


def test_compare_schedule_strategies_does_not_mutate_task(
    client: TestClient,
) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_valid_task_payload())
    task_id = create_response.json()["id"]

    response = client.get(f"/api/v1/tasks/{task_id}/schedule-comparison")

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    items = {item["strategy_name"]: item for item in body["items"]}
    assert set(items) == {"local_only", "random_offload", "greedy"}
    assert all(item["feasible"] for item in items.values())
    assert items["local_only"]["local_assignment_count"] == 1
    assert items["local_only"]["edge_assignment_count"] == 0
    assert items["greedy"]["edge_assignment_count"] == 1
    assert (
        items["greedy"]["estimated_total_duration_ms"]
        < items["local_only"]["estimated_total_duration_ms"]
    )

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.json()["status"] == "PENDING"


def test_compare_schedule_strategies_for_unknown_task_returns_404(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000001/schedule-comparison"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_list_task_schedules_returns_created_plan(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    schedule_id = schedule_response.json()["id"]

    response = client.get(f"/api/v1/tasks/{task_id}/schedules")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == schedule_id
    assert body["items"][0]["strategy_name"] == "greedy"
    assert body["items"][0]["status"] == "GENERATED"


def test_list_schedules_for_unknown_task_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000001/schedules"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_get_schedule_plan_returns_items(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    schedule_id = schedule_response.json()["id"]

    response = client.get(f"/api/v1/schedules/{schedule_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == schedule_id
    assert body["task_id"] == task_id
    assert body["strategy_name"] == "greedy"
    assert len(body["items"]) == 1


def test_get_unknown_schedule_plan_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/schedules/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCHEDULE_PLAN_NOT_FOUND"


def test_execute_task_starts_execution_from_schedule_plan(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    schedule_id = schedule_response.json()["id"]

    response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": schedule_id},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["task_id"] == task_id
    assert body["schedule_plan_id"] == schedule_id
    assert body["status"] == "RUNNING"
    assert body["execution_count"] == 1
    assert body["queued_count"] == 0

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    detail_body = detail_response.json()
    assert detail_body["status"] == "RUNNING"
    subtask_statuses = {
        subtask["external_id"]: subtask["status"]
        for subtask in detail_body["subtasks"]
    }
    assert subtask_statuses["capture_image"] == "RUNNING"

    schedule_detail_response = client.get(f"/api/v1/schedules/{schedule_id}")
    assert schedule_detail_response.json()["status"] == "APPLIED"


def test_execute_task_rejects_non_terminal_simulated_result_status(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000001/execute",
        json={
            "schedule_plan_id": "00000000-0000-0000-0000-000000000001",
            "simulation": {"result_status": "RUNNING"},
        },
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_execute_task_rejects_unscheduled_task(client: TestClient) -> None:
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": "00000000-0000-0000-0000-000000000001"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_STATE_CONFLICT"


def test_execute_task_rejects_unknown_schedule_plan(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": "00000000-0000-0000-0000-000000000001"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SCHEDULE_PLAN_NOT_FOUND"


def test_list_task_executions_returns_started_execution(client: TestClient) -> None:
    uav_id, _ = _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": schedule_response.json()["id"]},
    )
    execution_id = execute_response.json()["execution_ids"][0]

    response = client.get(f"/api/v1/tasks/{task_id}/executions")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == execution_id
    assert body["items"][0]["task_id"] == task_id
    assert body["items"][0]["node_id"] == uav_id
    assert body["items"][0]["attempt"] == 1
    assert body["items"][0]["status"] == "RUNNING"
    assert body["items"][0]["started_at"] is not None
    assert body["items"][0]["finished_at"] is None


def test_list_task_executions_filters_by_status(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": schedule_response.json()["id"]},
    )
    execution_id = execute_response.json()["execution_ids"][0]
    client.post(
        f"/api/v1/executions/{execution_id}/result",
        json={
            "status": "SUCCESS",
            "duration_ms": 800,
            "output_summary": "image captured",
        },
    )

    response = client.get(f"/api/v1/tasks/{task_id}/executions?status=SUCCESS")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == execution_id
    assert body["items"][0]["status"] == "SUCCESS"
    assert body["items"][0]["duration_ms"] == 800
    assert body["items"][0]["output_summary"] == "image captured"
    assert body["items"][0]["finished_at"] is not None


def test_list_task_executions_rejects_invalid_status_filter(
    client: TestClient,
) -> None:
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]

    response = client.get(f"/api/v1/tasks/{task_id}/executions?status=BAD_STATUS")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_list_task_executions_rejects_invalid_pagination(
    client: TestClient,
) -> None:
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]

    for query in ("page=0", "page_size=101"):
        response = client.get(f"/api/v1/tasks/{task_id}/executions?{query}")

        assert response.status_code == 422
        assert "detail" in response.json()


def test_list_executions_for_unknown_task_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000001/executions"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_report_execution_success_marks_successor_ready(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": schedule_response.json()["id"]},
    )
    execution_id = execute_response.json()["execution_ids"][0]

    response = client.post(
        f"/api/v1/executions/{execution_id}/result",
        json={
            "status": "SUCCESS",
            "duration_ms": 800,
            "output_summary": "image captured",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_id"] == execution_id
    assert body["accepted"] is True
    assert body["subtask_status"] == "SUCCESS"
    assert body["task_status"] == "RUNNING"

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    subtask_statuses = {
        subtask["external_id"]: subtask["status"]
        for subtask in detail_response.json()["subtasks"]
    }
    assert subtask_statuses["capture_image"] == "SUCCESS"
    assert subtask_statuses["detect_target"] == "READY"
    assert subtask_statuses["upload_report"] == "WAITING"


def test_duplicate_execution_success_result_is_ignored(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": schedule_response.json()["id"]},
    )
    execution_id = execute_response.json()["execution_ids"][0]
    first_response = client.post(
        f"/api/v1/executions/{execution_id}/result",
        json={
            "status": "SUCCESS",
            "duration_ms": 800,
            "output_summary": "image captured",
        },
    )

    duplicate_response = client.post(
        f"/api/v1/executions/{execution_id}/result",
        json={
            "status": "SUCCESS",
            "duration_ms": 999,
            "output_summary": "duplicate result should be ignored",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["accepted"] is True
    assert duplicate_response.status_code == 200
    duplicate_body = duplicate_response.json()
    assert duplicate_body["accepted"] is False
    assert duplicate_body["subtask_status"] == "SUCCESS"
    assert duplicate_body["task_status"] == "RUNNING"

    executions_response = client.get(f"/api/v1/tasks/{task_id}/executions")
    execution = executions_response.json()["items"][0]
    assert execution["status"] == "SUCCESS"
    assert execution["duration_ms"] == 800
    assert execution["output_summary"] == "image captured"


def test_late_failure_result_does_not_override_success(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": schedule_response.json()["id"]},
    )
    execution_id = execute_response.json()["execution_ids"][0]
    client.post(
        f"/api/v1/executions/{execution_id}/result",
        json={
            "status": "SUCCESS",
            "duration_ms": 800,
            "output_summary": "image captured",
        },
    )

    response = client.post(
        f"/api/v1/executions/{execution_id}/result",
        json={
            "status": "FAILED",
            "duration_ms": 1000,
            "failure_reason": "late failure should not override success",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["subtask_status"] == "SUCCESS"
    assert body["task_status"] == "RUNNING"

    executions_response = client.get(f"/api/v1/tasks/{task_id}/executions")
    execution = executions_response.json()["items"][0]
    assert execution["status"] == "SUCCESS"
    assert execution["failure_reason"] is None


def test_schedule_running_task_after_success_schedules_ready_successor(
    client: TestClient,
) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    first_schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    first_execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": first_schedule_response.json()["id"]},
    )
    first_execution_id = first_execute_response.json()["execution_ids"][0]
    client.post(
        f"/api/v1/executions/{first_execution_id}/result",
        json={
            "status": "SUCCESS",
            "duration_ms": 800,
            "output_summary": "image captured",
        },
    )
    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    detect_subtask_id = next(
        subtask["id"]
        for subtask in detail_response.json()["subtasks"]
        if subtask["external_id"] == "detect_target"
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["task_id"] == task_id
    assert body["status"] == "GENERATED"
    assert len(body["items"]) == 1
    assert body["items"][0]["subtask_id"] == detect_subtask_id

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.json()["status"] == "RUNNING"


def test_execute_running_task_starts_next_ready_successor(
    client: TestClient,
) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    first_schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    first_execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": first_schedule_response.json()["id"]},
    )
    first_execution_id = first_execute_response.json()["execution_ids"][0]
    client.post(
        f"/api/v1/executions/{first_execution_id}/result",
        json={
            "status": "SUCCESS",
            "duration_ms": 800,
            "output_summary": "image captured",
        },
    )
    second_schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )

    response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": second_schedule_response.json()["id"]},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["task_id"] == task_id
    assert body["status"] == "RUNNING"
    assert body["execution_count"] == 1

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    subtask_statuses = {
        subtask["external_id"]: subtask["status"]
        for subtask in detail_response.json()["subtasks"]
    }
    assert subtask_statuses["capture_image"] == "SUCCESS"
    assert subtask_statuses["detect_target"] == "RUNNING"
    assert subtask_statuses["upload_report"] == "WAITING"

    executions_response = client.get(f"/api/v1/tasks/{task_id}/executions")
    assert executions_response.json()["total"] == 2


def test_complete_dag_success_flow_marks_task_success(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]

    expected_steps = [
        ("capture_image", "image captured"),
        ("detect_target", "target detected"),
        ("upload_report", "report uploaded"),
    ]

    for step_index, (external_id, output_summary) in enumerate(expected_steps):
        detail_response = client.get(f"/api/v1/tasks/{task_id}")
        ready_subtasks = [
            subtask
            for subtask in detail_response.json()["subtasks"]
            if subtask["status"] == "READY"
        ]
        assert len(ready_subtasks) == 1
        assert ready_subtasks[0]["external_id"] == external_id

        schedule_response = client.post(
            f"/api/v1/tasks/{task_id}/schedule",
            json={"strategy_name": "greedy"},
        )
        assert schedule_response.status_code == 201
        schedule_body = schedule_response.json()
        assert len(schedule_body["items"]) == 1
        assert schedule_body["items"][0]["subtask_id"] == ready_subtasks[0]["id"]

        execute_response = client.post(
            f"/api/v1/tasks/{task_id}/execute",
            json={"schedule_plan_id": schedule_body["id"]},
        )
        assert execute_response.status_code == 202
        execution_id = execute_response.json()["execution_ids"][0]

        result_response = client.post(
            f"/api/v1/executions/{execution_id}/result",
            json={
                "status": "SUCCESS",
                "duration_ms": 800 + step_index * 100,
                "output_summary": output_summary,
            },
        )
        assert result_response.status_code == 200
        result_body = result_response.json()
        assert result_body["accepted"] is True
        assert result_body["subtask_status"] == "SUCCESS"
        expected_task_status = (
            "SUCCESS" if step_index == len(expected_steps) - 1 else "RUNNING"
        )
        assert result_body["task_status"] == expected_task_status

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    detail_body = detail_response.json()
    assert detail_body["status"] == "SUCCESS"
    assert {
        subtask["external_id"]: subtask["status"]
        for subtask in detail_body["subtasks"]
    } == {
        "capture_image": "SUCCESS",
        "detect_target": "SUCCESS",
        "upload_report": "SUCCESS",
    }

    executions_response = client.get(f"/api/v1/tasks/{task_id}/executions")
    assert executions_response.json()["total"] == 3

    schedules_response = client.get(f"/api/v1/tasks/{task_id}/schedules")
    assert schedules_response.json()["total"] == 3


def test_get_task_metrics_after_successful_dag(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]

    for step_index, output_summary in enumerate(
        ("image captured", "target detected", "report uploaded")
    ):
        schedule_response = client.post(
            f"/api/v1/tasks/{task_id}/schedule",
            json={"strategy_name": "greedy"},
        )
        execute_response = client.post(
            f"/api/v1/tasks/{task_id}/execute",
            json={"schedule_plan_id": schedule_response.json()["id"]},
        )
        execution_id = execute_response.json()["execution_ids"][0]
        client.post(
            f"/api/v1/executions/{execution_id}/result",
            json={
                "status": "SUCCESS",
                "duration_ms": 800 + step_index * 100,
                "output_summary": output_summary,
            },
        )

    response = client.get(f"/api/v1/tasks/{task_id}/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task_id
    assert body["task_status"] == "SUCCESS"
    assert body["total_subtask_count"] == 3
    assert body["success_subtask_count"] == 3
    assert body["failed_subtask_count"] == 0
    assert body["execution_count"] == 3
    assert body["success_execution_count"] == 3
    assert body["failed_execution_count"] == 0
    assert body["running_execution_count"] == 0
    assert body["success_rate"] == 1.0
    assert body["failure_rate"] == 0.0
    assert body["total_execution_duration_ms"] == 2700
    assert body["average_execution_duration_ms"] == 900.0
    assert body["local_execution_count"] == 1
    assert body["edge_execution_count"] == 2
    assert body["offload_rate"] == 0.6667


def test_get_task_metrics_before_execution_returns_zero_counts(
    client: TestClient,
) -> None:
    create_response = client.post("/api/v1/tasks", json=_valid_task_payload())
    task_id = create_response.json()["id"]

    response = client.get(f"/api/v1/tasks/{task_id}/metrics")

    assert response.status_code == 200
    body = response.json()
    assert body["task_status"] == "PENDING"
    assert body["total_subtask_count"] == 3
    assert body["execution_count"] == 0
    assert body["success_rate"] == 0.0
    assert body["failure_rate"] == 0.0
    assert body["total_execution_duration_ms"] == 0
    assert body["average_execution_duration_ms"] is None
    assert body["local_execution_count"] == 0
    assert body["edge_execution_count"] == 0


def test_get_metrics_for_unknown_task_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000001/metrics"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_report_retryable_execution_failure_marks_subtask_ready(
    client: TestClient,
) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": schedule_response.json()["id"]},
    )
    execution_id = execute_response.json()["execution_ids"][0]

    response = client.post(
        f"/api/v1/executions/{execution_id}/result",
        json={
            "status": "FAILED",
            "duration_ms": 800,
            "failure_reason": "camera unavailable",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["subtask_status"] == "READY"
    assert body["task_status"] == "RUNNING"

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    detail_body = detail_response.json()
    assert detail_body["status"] == "RUNNING"
    capture_subtask = next(
        subtask
        for subtask in detail_body["subtasks"]
        if subtask["external_id"] == "capture_image"
    )
    assert capture_subtask["status"] == "READY"
    assert capture_subtask["retry_count"] == 1


def test_duplicate_retryable_failure_does_not_increment_retry_count_twice(
    client: TestClient,
) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": schedule_response.json()["id"]},
    )
    execution_id = execute_response.json()["execution_ids"][0]
    first_response = client.post(
        f"/api/v1/executions/{execution_id}/result",
        json={
            "status": "FAILED",
            "duration_ms": 800,
            "failure_reason": "camera unavailable",
        },
    )

    duplicate_response = client.post(
        f"/api/v1/executions/{execution_id}/result",
        json={
            "status": "FAILED",
            "duration_ms": 1000,
            "failure_reason": "duplicate failure should be ignored",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["accepted"] is True
    assert duplicate_response.status_code == 200
    duplicate_body = duplicate_response.json()
    assert duplicate_body["accepted"] is False
    assert duplicate_body["subtask_status"] == "READY"
    assert duplicate_body["task_status"] == "RUNNING"

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    capture_subtask = next(
        subtask
        for subtask in detail_response.json()["subtasks"]
        if subtask["external_id"] == "capture_image"
    )
    assert capture_subtask["status"] == "READY"
    assert capture_subtask["retry_count"] == 1

    executions_response = client.get(f"/api/v1/tasks/{task_id}/executions")
    execution = executions_response.json()["items"][0]
    assert execution["status"] == "FAILED"
    assert execution["duration_ms"] == 800
    assert execution["failure_reason"] == "camera unavailable"


def test_retry_ready_subtask_can_be_scheduled_and_executed_again(
    client: TestClient,
) -> None:
    _create_ready_nodes(client)
    create_response = client.post("/api/v1/tasks", json=_local_capture_task_payload())
    task_id = create_response.json()["id"]
    first_schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    first_execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": first_schedule_response.json()["id"]},
    )
    first_execution_id = first_execute_response.json()["execution_ids"][0]
    client.post(
        f"/api/v1/executions/{first_execution_id}/result",
        json={
            "status": "FAILED",
            "duration_ms": 800,
            "failure_reason": "camera unavailable",
        },
    )

    retry_schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    retry_execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": retry_schedule_response.json()["id"]},
    )
    retry_execution_id = retry_execute_response.json()["execution_ids"][0]

    assert retry_execute_response.status_code == 202
    executions_response = client.get(f"/api/v1/tasks/{task_id}/executions")
    attempts = {
        item["id"]: item["attempt"] for item in executions_response.json()["items"]
    }
    assert attempts[first_execution_id] == 1
    assert attempts[retry_execution_id] == 2


def test_report_execution_failure_marks_task_failed(client: TestClient) -> None:
    _create_ready_nodes(client)
    create_response = client.post(
        "/api/v1/tasks",
        json=_non_retryable_local_capture_task_payload(),
    )
    task_id = create_response.json()["id"]
    schedule_response = client.post(
        f"/api/v1/tasks/{task_id}/schedule",
        json={"strategy_name": "greedy"},
    )
    execute_response = client.post(
        f"/api/v1/tasks/{task_id}/execute",
        json={"schedule_plan_id": schedule_response.json()["id"]},
    )
    execution_id = execute_response.json()["execution_ids"][0]

    response = client.post(
        f"/api/v1/executions/{execution_id}/result",
        json={
            "status": "FAILED",
            "duration_ms": 800,
            "failure_reason": "camera unavailable",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["subtask_status"] == "FAILED"
    assert body["task_status"] == "FAILED"

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.json()["status"] == "FAILED"


def test_report_unknown_execution_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/executions/00000000-0000-0000-0000-000000000001/result",
        json={"status": "SUCCESS"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EXECUTION_NOT_FOUND"


def test_create_task_rejects_cyclic_dag_without_persisting_task(
    client: TestClient,
) -> None:
    payload = _valid_task_payload()
    payload["dependencies"] = [
        {"from": "capture_image", "to": "detect_target"},
        {"from": "detect_target", "to": "upload_report"},
        {"from": "upload_report", "to": "capture_image"},
    ]

    response = client.post("/api/v1/tasks", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DAG_VALIDATION_FAILED"

    list_response = client.get("/api/v1/tasks")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0


def test_get_unknown_task_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"
