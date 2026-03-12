from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from jose import jwt

import app.main as gateway_main
from app.core.config import settings

client = TestClient(gateway_main.app)


def _make_token(scopes: list[str]) -> str:
    """Genere un token de test avec les claims souhaites."""
    now = datetime.now(UTC)
    payload = {
        "sub": "1",
        "email": "user@example.com",
        "roles": ["member"],
        "scopes": scopes,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _auth_headers(scopes: list[str]) -> dict[str, str]:
    """Construit les headers Authorization pour les tests API."""
    return {"Authorization": f"Bearer {_make_token(scopes)}"}


def test_root_and_health() -> None:
    """Teste le cas "root and health"."""
    gateway_main.rate_limiter.clear()
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["service"] == "api-gateway"

    live = client.get("/health/live")
    assert live.status_code == 200

    ready = client.get("/health/ready")
    assert ready.status_code == 200


def test_protected_route_without_token_returns_401() -> None:
    """Teste le cas "protected route without token returns 401"."""
    gateway_main.rate_limiter.clear()
    response = client.get("/tasks")
    assert response.status_code == 401


def test_invalid_token_returns_401() -> None:
    """Teste le cas "invalid token returns 401"."""
    gateway_main.rate_limiter.clear()
    response = client.get("/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_gateway_routes_to_query_for_get_tasks(monkeypatch) -> None:
    """Teste le cas "gateway routes to query for get tasks"."""
    gateway_main.rate_limiter.clear()
    captured: dict[str, str] = {}

    async def fake_proxy(target_base_url: str, request, correlation_id: str):
        """Simule un proxy upstream pour verifier le routage GET /tasks."""
        captured["target"] = target_base_url
        captured["path"] = request.url.path
        captured["correlation_id"] = correlation_id
        return gateway_main.JSONResponse(
            status_code=200,
            content={"ok": True},
        )

    monkeypatch.setattr(gateway_main, "_proxy_request", fake_proxy)
    response = client.get("/tasks", headers=_auth_headers(["task:read"]))

    assert response.status_code == 200
    assert captured["target"] == settings.query_service_url
    assert captured["path"] == "/tasks"
    assert response.headers["X-Correlation-Id"] == captured["correlation_id"]


def test_gateway_routes_to_task_for_put_task(monkeypatch) -> None:
    """Teste le cas "gateway routes to task for put task"."""
    gateway_main.rate_limiter.clear()
    captured: dict[str, str] = {}

    async def fake_proxy(target_base_url: str, request, correlation_id: str):
        """Simule un proxy upstream pour verifier le routage PUT /tasks/{id}."""
        captured["target"] = target_base_url
        captured["path"] = request.url.path
        captured["method"] = request.method
        return gateway_main.JSONResponse(status_code=200, content={"ok": True})

    monkeypatch.setattr(gateway_main, "_proxy_request", fake_proxy)
    response = client.put(
        "/tasks/10",
        headers=_auth_headers(["task:update"]),
        json={
            "title": "Task X",
            "description": None,
            "status": "open",
            "priority": "high",
            "assigned_to": None,
            "due_date": None,
        },
    )

    assert response.status_code == 200
    assert captured["target"] == settings.task_service_url
    assert captured["path"] == "/tasks/10"
    assert captured["method"] == "PUT"


def test_rate_limiting_returns_429() -> None:
    """Teste le cas "rate limiting returns 429"."""
    gateway_main.rate_limiter.clear()
    gateway_main.rate_limiter.requests_per_window = 1
    response_1 = client.get("/")
    response_2 = client.get("/")

    assert response_1.status_code == 200
    assert response_2.status_code == 429
    assert response_2.json()["detail"] == "Rate limit exceeded"

    gateway_main.rate_limiter.requests_per_window = 1000
