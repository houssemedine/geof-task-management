from datetime import datetime

from pydantic import BaseModel


class TaskReadResponse(BaseModel):
    """Modélise la structure "TaskReadResponse"."""

    task_id: int
    title: str
    description: str | None
    status: str
    priority: str
    created_by: int
    assigned_to: int | None
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Modélise la structure "TaskListResponse"."""

    items: list[TaskReadResponse]
    total: int
    page: int
    page_size: int


class AnalyticsOverviewResponse(BaseModel):
    """Modélise la structure "AnalyticsOverviewResponse"."""

    total_tasks: int
    unassigned_tasks: int
    overdue_tasks: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    generated_at: datetime
