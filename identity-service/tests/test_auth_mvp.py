from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import decode_access_token
from app.main import app
from app.models import User

client = TestClient(app)


def _register(email: str = "user@example.com", password: str = "StrongPass123!"):
    """Cree un nouvel utilisateur si l'email n'existe pas deja."""
    return client.post("/auth/register", json={"email": email, "password": password})


def _login(email: str = "user@example.com", password: str = "StrongPass123!"):
    """Authentifie un utilisateur et retourne un token JWT."""
    return client.post("/auth/login", json={"email": email, "password": password})


def test_register_returns_201_with_expected_fields() -> None:
    """Teste le cas "register returns 201 with expected fields"."""
    response = _register()

    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "user@example.com"
    assert payload["is_active"] is True
    assert payload["roles"] == ["member"]
    assert "created_at" in payload
    assert "updated_at" in payload
    assert "password" not in payload
    assert "password_hash" not in payload


def test_duplicate_register_returns_409() -> None:
    """Teste le cas "duplicate register returns 409"."""
    first = _register()
    assert first.status_code == 201

    second = _register()
    assert second.status_code == 409
    assert second.json()["detail"] == "Email already exists"


def test_login_with_valid_credentials_returns_token() -> None:
    """Teste le cas "login with valid credentials returns token"."""
    _register()
    response = _login()

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 900

    token_payload = decode_access_token(payload["access_token"])
    assert token_payload["sub"]
    assert token_payload["email"] == "user@example.com"
    assert token_payload["roles"] == ["member"]
    assert set(token_payload["scopes"]) == {"task:create", "task:read", "task:update"}
    assert token_payload["iss"] == "identity-service"
    assert token_payload["aud"] == "gf-task-management"


def test_login_with_invalid_password_returns_401() -> None:
    """Teste le cas "login with invalid password returns 401"."""
    _register()
    response = _login(password="wrongPass123")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_without_token_returns_401() -> None:
    """Teste le cas "me without token returns 401"."""
    _register()
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_with_valid_token_returns_200_and_user() -> None:
    """Teste le cas "me with valid token returns 200 and user"."""
    _register()
    login_response = _login()
    token = login_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "user@example.com"
    assert payload["roles"] == ["member"]
    assert "password" not in payload
    assert "password_hash" not in payload


def test_expired_token_is_rejected_by_me_with_401() -> None:
    """Teste le cas "expired token is rejected by me with 401"."""
    register_response = _register()
    user_id = register_response.json()["id"]

    now = datetime.now(UTC)
    expired_payload = {
        "sub": str(user_id),
        "email": "user@example.com",
        "roles": ["member"],
        "scopes": ["task:create", "task:read", "task:update"],
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


def test_password_is_stored_hashed_not_plaintext() -> None:
    """Teste le cas "password is stored hashed not plaintext"."""
    _register(password="StrongPass123!")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "user@example.com"))

    assert user is not None
    assert user.password_hash != "StrongPass123!"
    assert user.password_hash


def test_inactive_user_cannot_login_and_gets_403() -> None:
    """Teste le cas "inactive user cannot login and gets 403"."""
    _register()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        assert user is not None
        user.is_active = False
        db.add(user)
        db.commit()

    response = _login()

    assert response.status_code == 403
    assert response.json()["detail"] == "User is inactive"


def test_get_roles_returns_bootstrapped_roles() -> None:
    """Teste le cas "get roles returns bootstrapped roles"."""
    response = client.get("/roles")

    assert response.status_code == 200
    payload = response.json()
    role_names = {role["name"] for role in payload}
    assert "admin" in role_names
    assert "member" in role_names


def test_get_permissions_returns_bootstrapped_permissions() -> None:
    """Teste le cas "get permissions returns bootstrapped permissions"."""
    response = client.get("/permissions")

    assert response.status_code == 200
    payload = response.json()
    permission_names = {permission["name"] for permission in payload}
    assert "task:create" in permission_names
    assert "task:read" in permission_names
    assert "users:manage" in permission_names
