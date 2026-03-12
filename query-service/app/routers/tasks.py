from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_scopes
from app.models import TaskReadModel
from app.schemas import TaskListResponse, TaskReadResponse

router = APIRouter(tags=["tasks"])


def _to_response(task: TaskReadModel) -> TaskReadResponse:
    """Convertit le modele SQLAlchemy en schema de reponse API."""
    return TaskReadResponse(
        task_id=task.task_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        created_by=task.created_by,
        assigned_to=task.assigned_to,
        due_date=task.due_date,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
    assignee: int | None = None,
    _: dict = Depends(require_scopes(["task:read"])),
    db: Session = Depends(get_db),
) -> TaskListResponse:
    """Retourne la liste des taches selon les filtres fournis."""
    filters = []
    if status is not None:
        filters.append(TaskReadModel.status == status)
    if priority is not None:
        filters.append(TaskReadModel.priority == priority)
    if assignee is not None:
        filters.append(TaskReadModel.assigned_to == assignee)

    base_query = select(TaskReadModel)
    if filters:
        base_query = base_query.where(*filters)

    total_query = select(func.count()).select_from(TaskReadModel)
    if filters:
        total_query = total_query.where(*filters)

    total = db.scalar(total_query) or 0

    offset = (page - 1) * page_size
    rows = db.scalars(
        base_query.order_by(TaskReadModel.updated_at.desc()).offset(offset).limit(page_size)
    ).all()

    return TaskListResponse(
        items=[_to_response(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
