from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app
from app.models import TaskReadModel

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


def _insert_task(
    *,
    task_id: int,
    status: str,
    priority: str,
    assigned_to: int | None,
    updated_at: datetime,
) -> None:
    """Insere une tache de test dans la base read-side."""
    with SessionLocal() as db:
        db.add(
            TaskReadModel(
                task_id=task_id,
                title=f"Task {task_id}",
                description=None,
                status=status,
                priority=priority,
                created_by=1,
                assigned_to=assigned_to,
                due_date=None,
                created_at=updated_at - timedelta(minutes=5),
                updated_at=updated_at,
                last_event_at=updated_at,
            )
        )
        db.commit()


def test_list_tasks_paginates_and_orders_by_updated_at_desc() -> None:
    """Teste le cas "list tasks paginates and orders by updated at desc"."""
    now = datetime.now(UTC)
    _insert_task(task_id=1, status="open", priority="low", assigned_to=2, updated_at=now)
    _insert_task(
        task_id=2,
        status="in_progress",
        priority="high",
        assigned_to=3,
        updated_at=now + timedelta(minutes=2),
    )

    response = client.get("/tasks?page=1&page_size=1", headers=_auth_headers(["task:read"]))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 1
    assert payload["items"][0]["task_id"] == 2


def test_list_tasks_filters_by_status_priority_and_assignee() -> None:
    """Teste le cas "list tasks filters by status priority and assignee"."""
    now = datetime.now(UTC)
    _insert_task(task_id=3, status="open", priority="high", assigned_to=10, updated_at=now)
    _insert_task(task_id=4, status="open", priority="low", assigned_to=10, updated_at=now)
    _insert_task(task_id=5, status="done", priority="high", assigned_to=11, updated_at=now)

    response = client.get(
        "/tasks?status=open&priority=high&assignee=10",
        headers=_auth_headers(["task:read"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["task_id"] == 3


def test_list_tasks_without_token_returns_401() -> None:
    """Teste le cas "list tasks without token returns 401"."""
    response = client.get("/tasks")

    assert response.status_code == 401


def test_list_tasks_with_missing_scope_returns_403() -> None:
    """Teste le cas "list tasks with missing scope returns 403"."""
    response = client.get("/tasks", headers=_auth_headers(["task:create"]))

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing required scope: task:read"
