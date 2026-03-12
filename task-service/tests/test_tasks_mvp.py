from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app
from app.models import OutboxEvent

client = TestClient(app)


def _make_token(scopes: list[str], user_id: int = 1) -> str:
    """Genere un token de test avec les claims souhaites."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "email": "user@example.com",
        "roles": ["member"],
        "scopes": scopes,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _auth_headers(scopes: list[str]) -> dict[str, str]:
    """Construit les headers Authorization pour les tests API."""
    token = _make_token(scopes)
    return {"Authorization": f"Bearer {token}"}


def test_create_task_without_token_returns_401() -> None:
    """Teste le cas "create task without token returns 401"."""
    response = client.post("/tasks", json={"title": "Task A"})

    assert response.status_code == 401


def test_create_task_with_missing_scope_returns_403() -> None:
    """Teste le cas "create task with missing scope returns 403"."""
    response = client.post(
        "/tasks",
        headers=_auth_headers(["task:read"]),
        json={"title": "Task A"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing required scope: task:create"


def test_create_task_with_valid_scope_returns_201() -> None:
    """Teste le cas "create task with valid scope returns 201"."""
    response = client.post(
        "/tasks",
        headers=_auth_headers(["task:create"]),
        json={"title": "Task A", "priority": "high"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Task A"
    assert payload["status"] == "open"
    assert payload["priority"] == "high"
    assert payload["created_by"] == 1

    with SessionLocal() as db:
        latest_event = db.scalars(
            select(OutboxEvent).order_by(OutboxEvent.id.desc()).limit(1)
        ).first()
        assert latest_event is not None
        assert latest_event.event_type == "TaskCreated"
        assert latest_event.aggregate_id == payload["id"]


def test_get_task_requires_read_scope() -> None:
    """Teste le cas "get task requires read scope"."""
    create_response = client.post(
        "/tasks",
        headers=_auth_headers(["task:create"]),
        json={"title": "Task A"},
    )
    task_id = create_response.json()["id"]

    unauthorized_response = client.get(
        f"/tasks/{task_id}",
        headers=_auth_headers(["task:update"]),
    )
    assert unauthorized_response.status_code == 403

    authorized_response = client.get(
        f"/tasks/{task_id}",
        headers=_auth_headers(["task:read"]),
    )
    assert authorized_response.status_code == 200
    assert authorized_response.json()["id"] == task_id


def test_update_status_requires_update_scope_and_updates_task() -> None:
    """Teste le cas "update status requires update scope and updates task"."""
    create_response = client.post(
        "/tasks",
        headers=_auth_headers(["task:create"]),
        json={"title": "Task A"},
    )
    task_id = create_response.json()["id"]

    forbidden_response = client.post(
        f"/tasks/{task_id}/status",
        headers=_auth_headers(["task:read"]),
        json={"status": "in_progress"},
    )
    assert forbidden_response.status_code == 403

    updated_response = client.post(
        f"/tasks/{task_id}/status",
        headers=_auth_headers(["task:update"]),
        json={"status": "in_progress"},
    )

    assert updated_response.status_code == 200
    payload = updated_response.json()
    assert payload["status"] == "in_progress"

    with SessionLocal() as db:
        latest_event = db.scalars(
            select(OutboxEvent).order_by(OutboxEvent.id.desc()).limit(1)
        ).first()
        assert latest_event is not None
        assert latest_event.event_type == "TaskStatusChanged"
        assert latest_event.aggregate_id == task_id


def test_list_tasks_requires_read_scope_and_supports_filters() -> None:
    """Teste le cas "list tasks requires read scope and supports filters"."""
    first = client.post(
        "/tasks",
        headers=_auth_headers(["task:create"]),
        json={"title": "Task A", "priority": "high", "assigned_to": 3},
    )
    assert first.status_code == 201
    second = client.post(
        "/tasks",
        headers=_auth_headers(["task:create"]),
        json={"title": "Task B", "priority": "low", "assigned_to": 8},
    )
    assert second.status_code == 201

    forbidden = client.get("/tasks", headers=_auth_headers(["task:update"]))
    assert forbidden.status_code == 403

    response = client.get(
        "/tasks?page=1&page_size=10&priority=high&assignee=3",
        headers=_auth_headers(["task:read"]),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["title"] == "Task A"


def test_put_task_updates_fields_and_emits_updated_event() -> None:
    """Teste le cas "put task updates fields and emits updated event"."""
    create_response = client.post(
        "/tasks",
        headers=_auth_headers(["task:create"]),
        json={"title": "Task A"},
    )
    task_id = create_response.json()["id"]

    update_response = client.put(
        f"/tasks/{task_id}",
        headers=_auth_headers(["task:update"]),
        json={
            "title": "Task A Updated",
            "description": "new desc",
            "status": "in_progress",
            "priority": "high",
            "assigned_to": 12,
            "due_date": None,
        },
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["title"] == "Task A Updated"
    assert payload["status"] == "in_progress"
    assert payload["priority"] == "high"
    assert payload["assigned_to"] == 12

    with SessionLocal() as db:
        latest_event = db.scalars(
            select(OutboxEvent).order_by(OutboxEvent.id.desc()).limit(1)
        ).first()
        assert latest_event is not None
        assert latest_event.event_type == "TaskUpdated"
        assert latest_event.aggregate_id == task_id


def test_assign_task_requires_assign_scope_and_emits_assigned_event() -> None:
    """Teste le cas "assign task requires assign scope and emits assigned event"."""
    create_response = client.post(
        "/tasks",
        headers=_auth_headers(["task:create"]),
        json={"title": "Task A"},
    )
    task_id = create_response.json()["id"]

    forbidden = client.post(
        f"/tasks/{task_id}/assign",
        headers=_auth_headers(["task:update"]),
        json={"assigned_to": 20},
    )
    assert forbidden.status_code == 403

    assign_response = client.post(
        f"/tasks/{task_id}/assign",
        headers=_auth_headers(["task:assign"]),
        json={"assigned_to": 20},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["assigned_to"] == 20

    with SessionLocal() as db:
        latest_event = db.scalars(
            select(OutboxEvent).order_by(OutboxEvent.id.desc()).limit(1)
        ).first()
        assert latest_event is not None
        assert latest_event.event_type == "TaskAssigned"
        assert latest_event.aggregate_id == task_id


def test_delete_task_requires_delete_scope_and_emits_deleted_event() -> None:
    """Teste le cas "delete task requires delete scope and emits deleted event"."""
    create_response = client.post(
        "/tasks",
        headers=_auth_headers(["task:create"]),
        json={"title": "Task A"},
    )
    task_id = create_response.json()["id"]

    forbidden = client.delete(
        f"/tasks/{task_id}",
        headers=_auth_headers(["task:read"]),
    )
    assert forbidden.status_code == 403

    delete_response = client.delete(
        f"/tasks/{task_id}",
        headers=_auth_headers(["task:delete"]),
    )
    assert delete_response.status_code == 204

    missing_response = client.get(
        f"/tasks/{task_id}",
        headers=_auth_headers(["task:read"]),
    )
    assert missing_response.status_code == 404

    with SessionLocal() as db:
        latest_event = db.scalars(
            select(OutboxEvent).order_by(OutboxEvent.id.desc()).limit(1)
        ).first()
        assert latest_event is not None
        assert latest_event.event_type == "TaskDeleted"
        assert latest_event.aggregate_id == task_id
