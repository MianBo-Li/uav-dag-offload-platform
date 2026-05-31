from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models.node import Node, NodeStatusRecord
from app.domain.enums import NodeStatus, NodeType


class NodeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, node: Node) -> Node:
        self.db.add(node)
        self.db.flush()
        self.db.refresh(node)
        return node

    def get_by_id(self, node_id: UUID) -> Node | None:
        return self.db.get(Node, node_id)

    def get_by_name(self, name: str) -> Node | None:
        return self.db.scalar(select(Node).where(Node.name == name))

    def list_nodes(
        self,
        node_type: NodeType | None,
        status: NodeStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Node], int]:
        statement: Select[tuple[Node]] = select(Node)
        count_statement = select(func.count()).select_from(Node)

        if node_type is not None:
            statement = statement.where(Node.node_type == node_type)
            count_statement = count_statement.where(Node.node_type == node_type)
        if status is not None:
            statement = statement.where(Node.status == status)
            count_statement = count_statement.where(Node.status == status)

        total = self.db.scalar(count_statement) or 0
        items = list(
            self.db.scalars(
                statement.order_by(Node.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    def list_by_status(self, status: NodeStatus) -> list[Node]:
        return list(self.db.scalars(select(Node).where(Node.status == status)))

    def get_latest_status_record(self, node_id: UUID) -> NodeStatusRecord | None:
        return self.db.scalar(
            select(NodeStatusRecord)
            .where(NodeStatusRecord.node_id == node_id)
            .order_by(NodeStatusRecord.reported_at.desc())
            .limit(1)
        )

    def create_status_record(self, record: NodeStatusRecord) -> NodeStatusRecord:
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record

    def list_status_records(
        self,
        node_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[NodeStatusRecord], int]:
        count_statement = select(func.count()).select_from(NodeStatusRecord).where(
            NodeStatusRecord.node_id == node_id
        )
        total = self.db.scalar(count_statement) or 0
        items = list(
            self.db.scalars(
                select(NodeStatusRecord)
                .where(NodeStatusRecord.node_id == node_id)
                .order_by(NodeStatusRecord.reported_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total
