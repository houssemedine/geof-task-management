from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.db import SessionLocal
from app.core.events import apply_task_event
from app.models import ProcessedEvent, TaskReadModel


def _as_utc(value: datetime) -> datetime:
    """Normalise une date en UTC pour des assertions robustes."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _event(
    event_type: str,
    occurred_at: datetime,
    payload: dict,
    *,
    event_id: str | None = None,
) -> dict:
    """Construit une enveloppe d'evenement de test."""
    return {
        "event_id": event_id or str(uuid4()),
        "event_type": event_type,
        "event_version": 1,
        "occurred_at": occurred_at.isoformat(),
        "producer": "task-service",
        "correlation_id": "corr-1",
        "payload": payload,
    }


def _payload(
    task_id: int,
    *,
    status: str = "open",
    updated_at: datetime,
) -> dict:
    """Construit un payload task de test."""
    return {
        "id": task_id,
        "title": "Task A",
        "description": "desc",
        "status": status,
        "priority": "high",
        "created_by": 1,
        "assigned_to": 9,
        "due_date": None,
        "created_at": (updated_at - timedelta(minutes=5)).isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def test_apply_task_created_inserts_projection() -> None:
    """Teste le cas "apply task created inserts projection"."""
    now = datetime.now(UTC)
    apply_task_event(_event("TaskCreated", now, _payload(10, updated_at=now)))

    with SessionLocal() as db:
        task = db.get(TaskReadModel, 10)
        assert task is not None
        assert task.title == "Task A"
        assert task.status == "open"
        assert task.priority == "high"
        assert task.created_by == 1
        assert task.assigned_to == 9


def test_apply_status_changed_updates_existing_task() -> None:
    """Teste le cas "apply status changed updates existing task"."""
    now = datetime.now(UTC)
    apply_task_event(_event("TaskCreated", now, _payload(11, status="open", updated_at=now)))

    later = now + timedelta(minutes=3)
    apply_task_event(
        _event(
            "TaskStatusChanged",
            later,
            _payload(11, status="in_progress", updated_at=later),
        )
    )

    with SessionLocal() as db:
        task = db.get(TaskReadModel, 11)
        assert task is not None
        assert task.status == "in_progress"
        assert _as_utc(task.last_event_at) == _as_utc(later)


def test_out_of_order_event_is_ignored() -> None:
    """Teste le cas "out of order event is ignored"."""
    now = datetime.now(UTC)
    apply_task_event(_event("TaskCreated", now, _payload(12, status="open", updated_at=now)))

    latest = now + timedelta(minutes=4)
    apply_task_event(
        _event("TaskStatusChanged", latest, _payload(12, status="done", updated_at=latest))
    )

    stale = now + timedelta(minutes=1)
    apply_task_event(
        _event(
            "TaskStatusChanged",
            stale,
            _payload(12, status="in_progress", updated_at=stale),
        )
    )

    with SessionLocal() as db:
        task = db.get(TaskReadModel, 12)
        assert task is not None
        assert task.status == "done"


def test_apply_task_updated_overwrites_projection_fields() -> None:
    """Teste le cas "apply task updated overwrites projection fields"."""
    now = datetime.now(UTC)
    apply_task_event(_event("TaskCreated", now, _payload(20, updated_at=now)))

    later = now + timedelta(minutes=5)
    updated_payload = _payload(20, updated_at=later)
    updated_payload["title"] = "Task A updated"
    updated_payload["priority"] = "low"
    apply_task_event(_event("TaskUpdated", later, updated_payload))

    with SessionLocal() as db:
        task = db.get(TaskReadModel, 20)
        assert task is not None
        assert task.title == "Task A updated"
        assert task.priority == "low"


def test_apply_task_assigned_updates_assignee() -> None:
    """Teste le cas "apply task assigned updates assignee"."""
    now = datetime.now(UTC)
    apply_task_event(_event("TaskCreated", now, _payload(21, updated_at=now)))

    later = now + timedelta(minutes=5)
    assigned_payload = _payload(21, updated_at=later)
    assigned_payload["assigned_to"] = 77
    apply_task_event(_event("TaskAssigned", later, assigned_payload))

    with SessionLocal() as db:
        task = db.get(TaskReadModel, 21)
        assert task is not None
        assert task.assigned_to == 77


def test_apply_task_deleted_removes_projection() -> None:
    """Teste le cas "apply task deleted removes projection"."""
    now = datetime.now(UTC)
    apply_task_event(_event("TaskCreated", now, _payload(22, updated_at=now)))

    later = now + timedelta(minutes=4)
    apply_task_event(_event("TaskDeleted", later, {"id": 22}))

    with SessionLocal() as db:
        task = db.get(TaskReadModel, 22)
        assert task is None


def test_duplicate_event_id_is_ignored_by_processed_events() -> None:
    """Teste le cas "duplicate event id is ignored by processed events"."""
    now = datetime.now(UTC)
    event_id = "evt-duplicate-1"
    apply_task_event(_event("TaskCreated", now, _payload(23, updated_at=now), event_id=event_id))
    apply_task_event(
        _event(
            "TaskUpdated",
            now + timedelta(minutes=2),
            _payload(23, updated_at=now + timedelta(minutes=2), status="done"),
            event_id=event_id,
        )
    )

    with SessionLocal() as db:
        task = db.get(TaskReadModel, 23)
        assert task is not None
        assert task.status == "open"
        assert db.get(ProcessedEvent, event_id) is not None
