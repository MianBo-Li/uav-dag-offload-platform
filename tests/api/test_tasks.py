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
