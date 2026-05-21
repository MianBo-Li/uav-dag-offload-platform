from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.node import Node, NodeStatusRecord
from app.domain.enums import NodeStatus, NodeType
from app.repositories.node_repository import NodeRepository
from app.schemas.node import NodeCreate, NodeStatusCreate


class NodeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = NodeRepository(db)

    def create_node(self, data: NodeCreate) -> Node:
        if self.repository.get_by_name(data.name) is not None:
            raise AppError(
                code="NODE_NAME_CONFLICT",
                message="Node name already exists",
                status_code=409,
                details={"name": data.name},
            )

        node = Node(
            name=data.name,
            node_type=data.node_type,
            status=NodeStatus.ONLINE,
            cpu_capacity=data.cpu_capacity,
            memory_capacity_mb=data.memory_capacity_mb,
            network_address=data.network_address,
            description=data.description,
        )
        return self.repository.create(node)

    def get_node(self, node_id: UUID) -> Node:
        node = self.repository.get_by_id(node_id)
        if node is None:
            raise AppError(
                code="NODE_NOT_FOUND",
                message="Node not found",
                status_code=404,
                details={"node_id": str(node_id)},
            )
        return node

    def list_nodes(
        self,
        node_type: NodeType | None,
        status: NodeStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Node], int]:
        return self.repository.list_nodes(node_type, status, page, page_size)

    def report_status(self, node_id: UUID, data: NodeStatusCreate) -> NodeStatusRecord:
        node = self.get_node(node_id)
        record = NodeStatusRecord(
            node_id=node.id,
            battery_level=data.battery_level,
            cpu_usage=data.cpu_usage,
            memory_usage=data.memory_usage,
            network_quality=data.network_quality,
            bandwidth_mbps=data.bandwidth_mbps,
            latitude=data.latitude,
            longitude=data.longitude,
            current_load=data.current_load,
            queue_length=data.queue_length,
            reported_at=data.reported_at,
        )

        node.last_heartbeat_at = data.reported_at
        node.status = self._resolve_node_status(data)
        saved_record = self.repository.create_status_record(record)
        self.db.flush()
        self.db.refresh(node)
        return saved_record

    def list_status_records(
        self,
        node_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[NodeStatusRecord], int]:
        self.get_node(node_id)
        return self.repository.list_status_records(node_id, page, page_size)

    @staticmethod
    def _resolve_node_status(data: NodeStatusCreate) -> NodeStatus:
        high_queue = data.queue_length is not None and data.queue_length >= 10
        high_load = data.current_load is not None and data.current_load >= 10
        if data.cpu_usage >= 90 or data.memory_usage >= 90 or high_queue or high_load:
            return NodeStatus.BUSY
        return NodeStatus.ONLINE
