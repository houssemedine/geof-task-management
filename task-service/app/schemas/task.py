from datetime import datetime

from pydantic import BaseModel, Field

from app.models import TaskPriority, TaskStatus


class TaskCreateRequest(BaseModel):
    """Modélise la structure "TaskCreateRequest"."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: int | None = None
    due_date: datetime | None = None


class TaskUpdateRequest(BaseModel):
    """Modélise la structure "TaskUpdateRequest"."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus = TaskStatus.OPEN
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: int | None = None
    due_date: datetime | None = None


class TaskStatusUpdateRequest(BaseModel):
    """Modélise la structure "TaskStatusUpdateRequest"."""

    status: TaskStatus


class TaskAssignRequest(BaseModel):
    """Modélise la structure "TaskAssignRequest"."""

    assigned_to: int | None = None


class TaskResponse(BaseModel):
    """Modélise la structure "TaskResponse"."""

    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    created_by: int
    assigned_to: int | None
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Modélise la structure "TaskListResponse"."""

    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
