from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.node import Node
from app.db.models.task import ExecutionRecord
from app.domain.enums import ExecutionStatus, NodeType


class ExecutionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_many(self, records: list[ExecutionRecord]) -> list[ExecutionRecord]:
        self.db.add_all(records)
        self.db.flush()
        return records

    def get_by_id(self, execution_id: UUID) -> ExecutionRecord | None:
        return self.db.scalar(self._get_by_id_statement(execution_id))

    def get_by_id_for_update(self, execution_id: UUID) -> ExecutionRecord | None:
        return self.db.scalar(
            self._get_by_id_statement(execution_id).with_for_update()
        )

    @staticmethod
    def _get_by_id_statement(execution_id: UUID) -> Select[tuple[ExecutionRecord]]:
        return (
            select(ExecutionRecord)
            .options(
                selectinload(ExecutionRecord.subtask),
                selectinload(ExecutionRecord.task),
            )
            .where(ExecutionRecord.id == execution_id)
        )

    def list_by_task(
        self,
        task_id: UUID,
        status: ExecutionStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ExecutionRecord], int]:
        statement: Select[tuple[ExecutionRecord]] = select(ExecutionRecord).where(
            ExecutionRecord.task_id == task_id
        )
        count_statement = (
            select(func.count())
            .select_from(ExecutionRecord)
            .where(ExecutionRecord.task_id == task_id)
        )

        if status is not None:
            statement = statement.where(ExecutionRecord.status == status)
            count_statement = count_statement.where(ExecutionRecord.status == status)

        total = self.db.scalar(count_statement) or 0
        items = list(
            self.db.scalars(
                statement.order_by(ExecutionRecord.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    def list_running_by_task_for_update(self, task_id: UUID) -> list[ExecutionRecord]:
        return list(
            self.db.scalars(
                select(ExecutionRecord)
                .where(
                    ExecutionRecord.task_id == task_id,
                    ExecutionRecord.status == ExecutionStatus.RUNNING,
                )
                .with_for_update()
            )
        )

    def list_all_by_task(self, task_id: UUID) -> list[ExecutionRecord]:
        return list(
            self.db.scalars(
                select(ExecutionRecord)
                .where(ExecutionRecord.task_id == task_id)
                .order_by(ExecutionRecord.created_at.asc())
            )
        )

    def count_by_node_type(self, task_id: UUID) -> dict[NodeType, int]:
        rows = self.db.execute(
            select(Node.node_type, func.count())
            .join(ExecutionRecord, ExecutionRecord.node_id == Node.id)
            .where(ExecutionRecord.task_id == task_id)
            .group_by(Node.node_type)
        )
        return {NodeType(node_type): count for node_type, count in rows}
