from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_scopes
from app.core.events import stage_task_event
from app.models import Task
from app.schemas import (
    TaskAssignRequest,
    TaskCreateRequest,
    TaskListResponse,
    TaskResponse,
    TaskStatusUpdateRequest,
    TaskUpdateRequest,
)

router = APIRouter(tags=["tasks"])


def _to_task_response(task: Task) -> TaskResponse:
    """Convertit le modele Task vers le schema de reponse API."""
    return TaskResponse(
        id=task.id,
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


def _to_task_event_payload(task: Task) -> dict:
    """Construit le payload standard des evenements task."""

    def _iso_or_none(value: datetime | None) -> str | None:
        """Convertit une date en ISO8601 ou retourne None."""
        return value.isoformat() if value is not None else None

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "priority": task.priority.value,
        "created_by": task.created_by,
        "assigned_to": task.assigned_to,
        "due_date": _iso_or_none(task.due_date),
        "created_at": _iso_or_none(task.created_at),
        "updated_at": _iso_or_none(task.updated_at),
    }


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest,
    token_payload: dict = Depends(require_scopes(["task:create"])),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Cree une tache puis publie l'evenement TaskCreated."""
    try:
        actor_id = int(token_payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    task = Task(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        created_by=actor_id,
        assigned_to=payload.assigned_to,
        due_date=payload.due_date,
    )
    db.add(task)
    db.flush()
    db.refresh(task)

    stage_task_event(
        db=db,
        event_type="TaskCreated",
        payload=_to_task_event_payload(task),
        aggregate_id=task.id,
        correlation_id=str(task.id),
    )
    db.commit()
    db.refresh(task)

    return _to_task_response(task)


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    priority_filter: str | None = Query(default=None, alias="priority"),
    assignee: int | None = Query(default=None),
    _: dict = Depends(require_scopes(["task:read"])),
    db: Session = Depends(get_db),
) -> TaskListResponse:
    """Retourne la liste des taches selon les filtres fournis."""
    filters = []
    if status_filter is not None:
        filters.append(Task.status == status_filter)
    if priority_filter is not None:
        filters.append(Task.priority == priority_filter)
    if assignee is not None:
        filters.append(Task.assigned_to == assignee)

    base_query = select(Task)
    if filters:
        base_query = base_query.where(*filters)

    total_query = select(func.count()).select_from(Task)
    if filters:
        total_query = total_query.where(*filters)

    total = db.scalar(total_query) or 0

    offset = (page - 1) * page_size
    rows = db.scalars(
        base_query.order_by(Task.updated_at.desc()).offset(offset).limit(page_size)
    ).all()

    return TaskListResponse(
        items=[_to_task_response(task) for task in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    _: dict = Depends(require_scopes(["task:read"])),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Retourne une tache par son identifiant."""
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return _to_task_response(task)


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdateRequest,
    _: dict = Depends(require_scopes(["task:update"])),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Met a jour une tache puis publie l'evenement TaskUpdated."""
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task.title = payload.title
    task.description = payload.description
    task.status = payload.status
    task.priority = payload.priority
    task.assigned_to = payload.assigned_to
    task.due_date = payload.due_date
    db.add(task)
    db.flush()
    db.refresh(task)

    stage_task_event(
        db=db,
        event_type="TaskUpdated",
        payload=_to_task_event_payload(task),
        aggregate_id=task.id,
        correlation_id=str(task.id),
    )
    db.commit()
    db.refresh(task)

    return _to_task_response(task)


@router.post("/tasks/{task_id}/assign", response_model=TaskResponse)
def assign_task(
    task_id: int,
    payload: TaskAssignRequest,
    _: dict = Depends(require_scopes(["task:assign"])),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Assigne une tache a un utilisateur puis publie TaskAssigned."""
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task.assigned_to = payload.assigned_to
    db.add(task)
    db.flush()
    db.refresh(task)

    stage_task_event(
        db=db,
        event_type="TaskAssigned",
        payload=_to_task_event_payload(task),
        aggregate_id=task.id,
        correlation_id=str(task.id),
    )
    db.commit()
    db.refresh(task)

    return _to_task_response(task)


@router.post("/tasks/{task_id}/status", response_model=TaskResponse)
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdateRequest,
    _: dict = Depends(require_scopes(["task:update"])),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Change le statut d'une tache puis publie TaskStatusChanged."""
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task.status = payload.status
    db.add(task)
    db.flush()
    db.refresh(task)

    stage_task_event(
        db=db,
        event_type="TaskStatusChanged",
        payload=_to_task_event_payload(task),
        aggregate_id=task.id,
        correlation_id=str(task.id),
    )
    db.commit()
    db.refresh(task)

    return _to_task_response(task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    _: dict = Depends(require_scopes(["task:delete"])),
    db: Session = Depends(get_db),
) -> Response:
    """Supprime une tache puis publie l'evenement TaskDeleted."""
    task = db.scalar(select(Task).where(Task.id == task_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    deleted_payload = {
        "id": task.id,
        "deleted_at": datetime.now(UTC).isoformat(),
    }
    db.delete(task)
    stage_task_event(
        db=db,
        event_type="TaskDeleted",
        payload=deleted_payload,
        aggregate_id=task_id,
        correlation_id=str(task_id),
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
