from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root() -> None:
    """Teste le cas "root"."""
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "query-service"
    assert payload["status"] == "ok"
    assert "version" in payload


def test_health_live() -> None:
    """Teste le cas "health live"."""
    response = client.get("/health/live")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "query-service"
    assert payload["status"] == "alive"


def test_health_ready() -> None:
    """Teste le cas "health ready"."""
    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "query-service"
    assert payload["status"] == "ready"
    assert "checked_at" in payload
    datetime.fromisoformat(payload["checked_at"])
