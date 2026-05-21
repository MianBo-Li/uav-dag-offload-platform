from datetime import UTC, datetime

from fastapi.testclient import TestClient


def test_create_node(client: TestClient) -> None:
    response = client.post(
        "/api/v1/nodes",
        json={
            "name": "UAV-001",
            "node_type": "UAV",
            "cpu_capacity": 100.0,
            "memory_capacity_mb": 2048,
            "network_address": "uav-001.local",
            "description": "inspection uav",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "UAV-001"
    assert body["node_type"] == "UAV"
    assert body["status"] == "ONLINE"


def test_create_node_rejects_duplicate_name(client: TestClient) -> None:
    payload = {
        "name": "EDGE-001",
        "node_type": "EDGE",
        "cpu_capacity": 500.0,
        "memory_capacity_mb": 16384,
    }

    assert client.post("/api/v1/nodes", json=payload).status_code == 201
    response = client.post("/api/v1/nodes", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NODE_NAME_CONFLICT"


def test_list_nodes_filters_by_type_and_status(client: TestClient) -> None:
    client.post(
        "/api/v1/nodes",
        json={
            "name": "UAV-001",
            "node_type": "UAV",
            "cpu_capacity": 100.0,
            "memory_capacity_mb": 2048,
        },
    )
    client.post(
        "/api/v1/nodes",
        json={
            "name": "EDGE-001",
            "node_type": "EDGE",
            "cpu_capacity": 500.0,
            "memory_capacity_mb": 16384,
        },
    )

    response = client.get("/api/v1/nodes?node_type=UAV&status=ONLINE")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "UAV-001"


def test_report_node_status_updates_node_and_creates_record(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/nodes",
        json={
            "name": "UAV-001",
            "node_type": "UAV",
            "cpu_capacity": 100.0,
            "memory_capacity_mb": 2048,
        },
    )
    node_id = create_response.json()["id"]
    reported_at = datetime(2026, 5, 21, 12, 0, tzinfo=UTC).isoformat()

    response = client.post(
        f"/api/v1/nodes/{node_id}/status",
        json={
            "battery_level": 82.5,
            "cpu_usage": 35.0,
            "memory_usage": 40.0,
            "network_quality": 85.0,
            "bandwidth_mbps": 12.5,
            "latitude": 31.230416,
            "longitude": 121.473701,
            "current_load": 1,
            "queue_length": 2,
            "reported_at": reported_at,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ONLINE"

    node_response = client.get(f"/api/v1/nodes/{node_id}")
    assert node_response.json()["last_heartbeat_at"] is not None

    records_response = client.get(f"/api/v1/nodes/{node_id}/status-records")
    records_body = records_response.json()
    assert records_body["total"] == 1
    assert records_body["items"][0]["cpu_usage"] == 35.0


def test_report_node_status_marks_busy_for_high_usage(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/nodes",
        json={
            "name": "EDGE-001",
            "node_type": "EDGE",
            "cpu_capacity": 500.0,
            "memory_capacity_mb": 16384,
        },
    )
    node_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/nodes/{node_id}/status",
        json={
            "cpu_usage": 95.0,
            "memory_usage": 40.0,
            "reported_at": datetime(2026, 5, 21, 12, 0, tzinfo=UTC).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "BUSY"


def test_get_unknown_node_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/nodes/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NODE_NOT_FOUND"
