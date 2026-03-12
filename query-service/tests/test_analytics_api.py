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
    due_date: datetime | None,
) -> None:
    """Insere une tache de test dans la base read-side."""
    now = datetime.now(UTC)
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
                due_date=due_date,
                created_at=now - timedelta(minutes=8),
                updated_at=now - timedelta(minutes=2),
                last_event_at=now - timedelta(minutes=2),
            )
        )
        db.commit()


def test_analytics_overview_requires_token() -> None:
    """Teste le cas "analytics overview requires token"."""
    response = client.get("/analytics/overview")
    assert response.status_code == 401


def test_analytics_overview_requires_analytics_read_scope() -> None:
    """Teste le cas "analytics overview requires analytics read scope"."""
    response = client.get("/analytics/overview", headers=_auth_headers(["task:read"]))
    assert response.status_code == 403
    assert response.json()["detail"] == "Missing required scope: analytics:read"


def test_analytics_overview_returns_expected_aggregates() -> None:
    """Teste le cas "analytics overview returns expected aggregates"."""
    now = datetime.now(UTC)
    _insert_task(
        task_id=100,
        status="open",
        priority="high",
        assigned_to=None,
        due_date=now - timedelta(days=1),
    )
    _insert_task(
        task_id=101,
        status="in_progress",
        priority="medium",
        assigned_to=11,
        due_date=now + timedelta(days=2),
    )
    _insert_task(
        task_id=102,
        status="done",
        priority="low",
        assigned_to=15,
        due_date=now - timedelta(days=2),
    )

    response = client.get("/analytics/overview", headers=_auth_headers(["analytics:read"]))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_tasks"] == 3
    assert payload["unassigned_tasks"] == 1
    assert payload["overdue_tasks"] == 1
    assert payload["by_status"]["open"] == 1
    assert payload["by_status"]["in_progress"] == 1
    assert payload["by_status"]["done"] == 1
