from datetime import UTC, datetime

from fastapi.testclient import TestClient


def _single_subtask_payload() -> dict[str, object]:
    return {
        "name": "monitoring-smoke-task",
        "priority": 1,
        "subtasks": [
            {
                "external_id": "capture_image",
                "name": "Capture image",
                "compute_load": 80.0,
                "input_data_size_mb": 0.0,
                "output_data_size_mb": 120.0,
                "execution_constraint": "LOCAL_ONLY",
                "max_retries": 1,
            }
        ],
        "dependencies": [],
        "metadata": {"source": "monitoring-test"},
    }


def _create_ready_uav(client: TestClient) -> str:
    node_response = client.post(
        "/api/v1/nodes",
        json={
            "name": "METRICS-UAV-001",
            "node_type": "UAV",
            "cpu_capacity": 100.0,
            "memory_capacity_mb": 2048,
        },
    )
    node_id = node_response.json()["id"]
    client.post(
        f"/api/v1/nodes/{node_id}/status",
        json={
            "cpu_usage": 0.0,
            "memory_usage": 30.0,
            "reported_at": datetime(2026, 5, 31, 12, 0, tzinfo=UTC).isoformat(),
        },
    )
    return node_id


def test_prometheus_metrics_empty_database(client: TestClient) -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "# HELP uav_dag_nodes_total Current number of registered nodes." in body
    assert "uav_dag_nodes_total 0" in body
    assert "uav_dag_tasks_total 0" in body
    assert "uav_dag_executions_total 0" in body
    assert "uav_dag_execution_duration_ms_sum 0" in body
    assert "uav_dag_execution_duration_ms_count 0" in body
    assert "uav_dag_worker_auto_enqueue_enabled 0" in body
    assert "uav_dag_worker_retry_max_retries 3" in body
    assert 'uav_dag_queue_monitor_enabled{queue="uav_dag_execution"} 0' in body
    assert 'uav_dag_queue_monitor_available{queue="uav_dag_execution"} 0' in body
    assert 'uav_dag_queue_messages{queue="uav_dag_execution"} 0' in body
    assert 'uav_dag_queue_messages_ready{queue="uav_dag_execution"} 0' in body
    assert 'uav_dag_queue_messages_unacknowledged{queue="uav_dag_execution"} 0' in body
    assert 'uav_dag_queue_consumers{queue="uav_dag_execution"} 0' in body


def test_prometheus_metrics_after_execution(client: TestClient) -> None:
    _create_ready_uav(client)
    task_response = client.post("/api/v1/tasks", json=_single_subtask_payload())
    task_id = task_response.json()["id"]
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
            "duration_ms": 1234,
            "output_summary": "image captured",
        },
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "uav_dag_nodes_total 1" in body
    assert 'uav_dag_nodes_by_type_total{node_type="UAV"} 1' in body
    assert 'uav_dag_tasks_by_status_total{status="SUCCESS"} 1' in body
    assert 'uav_dag_subtasks_by_status_total{status="SUCCESS"} 1' in body
    assert 'uav_dag_schedule_plans_by_status_total{status="APPLIED"} 1' in body
    assert 'uav_dag_executions_by_status_total{status="SUCCESS"} 1' in body
    assert "uav_dag_execution_duration_ms_sum 1234" in body
    assert "uav_dag_execution_duration_ms_count 1" in body
