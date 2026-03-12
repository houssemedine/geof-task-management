from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.dependencies import require_scopes
from app.models import TaskReadModel
from app.schemas import AnalyticsOverviewResponse

router = APIRouter(tags=["analytics"])


@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
def analytics_overview(
    _: dict = Depends(require_scopes(["analytics:read"])),
    db: Session = Depends(get_db),
) -> AnalyticsOverviewResponse:
    """Retourne les indicateurs agreges pour le tableau de bord."""
    total_tasks = db.scalar(select(func.count()).select_from(TaskReadModel)) or 0
    unassigned_tasks = (
        db.scalar(
            select(func.count())
            .select_from(TaskReadModel)
            .where(TaskReadModel.assigned_to.is_(None))
        )
        or 0
    )
    overdue_tasks = (
        db.scalar(
            select(func.count())
            .select_from(TaskReadModel)
            .where(
                TaskReadModel.due_date.is_not(None),
                TaskReadModel.due_date < datetime.now(UTC),
                TaskReadModel.status != "done",
            )
        )
        or 0
    )

    status_rows = db.execute(
        select(TaskReadModel.status, func.count())
        .group_by(TaskReadModel.status)
        .order_by(TaskReadModel.status.asc())
    ).all()
    priority_rows = db.execute(
        select(TaskReadModel.priority, func.count())
        .group_by(TaskReadModel.priority)
        .order_by(TaskReadModel.priority.asc())
    ).all()

    return AnalyticsOverviewResponse(
        total_tasks=total_tasks,
        unassigned_tasks=unassigned_tasks,
        overdue_tasks=overdue_tasks,
        by_status={status: int(count) for status, count in status_rows},
        by_priority={priority: int(count) for priority, count in priority_rows},
        generated_at=datetime.now(UTC),
    )
