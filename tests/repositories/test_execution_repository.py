from typing import Any
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.repositories.execution_repository import ExecutionRepository


class StatementCaptureSession:
    def __init__(self) -> None:
        self.statement: Any = None

    def scalar(self, statement: Any) -> None:
        self.statement = statement
        return None


def test_get_by_id_for_update_compiles_to_postgresql_row_lock() -> None:
    session = StatementCaptureSession()
    repository = ExecutionRepository(session)

    repository.get_by_id_for_update(uuid4())

    assert session.statement is not None
    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql
