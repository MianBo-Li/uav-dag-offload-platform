from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import NodeStatus, NodeType
from app.schemas.node import (
    NodeCreate,
    NodeListResponse,
    NodeRead,
    NodeStatusCreate,
    NodeStatusRecordListResponse,
    NodeStatusReportResponse,
)
from app.services.node_service import NodeService

router = APIRouter(prefix="/nodes")


@router.post("", response_model=NodeRead, status_code=status.HTTP_201_CREATED)
def create_node(payload: NodeCreate, db: Session = Depends(get_db)) -> NodeRead:
    node = NodeService(db).create_node(payload)
    db.commit()
    db.refresh(node)
    return NodeRead.model_validate(node)


@router.get("", response_model=NodeListResponse)
def list_nodes(
    node_type: NodeType | None = None,
    status_filter: NodeStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> NodeListResponse:
    items, total = NodeService(db).list_nodes(node_type, status_filter, page, page_size)
    return NodeListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{node_id}", response_model=NodeRead)
def get_node(node_id: UUID, db: Session = Depends(get_db)) -> NodeRead:
    node = NodeService(db).get_node(node_id)
    return NodeRead.model_validate(node)


@router.post("/{node_id}/status", response_model=NodeStatusReportResponse)
def report_node_status(
    node_id: UUID,
    payload: NodeStatusCreate,
    db: Session = Depends(get_db),
) -> NodeStatusReportResponse:
    service = NodeService(db)
    record = service.report_status(node_id, payload)
    db.commit()
    node = service.get_node(node_id)
    return NodeStatusReportResponse(
        id=record.id,
        node_id=record.node_id,
        status=node.status,
        reported_at=record.reported_at,
        created_at=record.created_at,
    )


@router.get("/{node_id}/status-records", response_model=NodeStatusRecordListResponse)
def list_node_status_records(
    node_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> NodeStatusRecordListResponse:
    items, total = NodeService(db).list_status_records(node_id, page, page_size)
    return NodeStatusRecordListResponse(items=items, page=page, page_size=page_size, total=total)
