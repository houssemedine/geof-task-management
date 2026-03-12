# Identity Service

Service FastAPI responsable de l'authentification et du RBAC.

## Responsibilities

- Register/login users
- Issue JWT access tokens
- Expose current user profile
- Expose RBAC catalog (roles and permissions)
- Seed default RBAC data (`admin`, `member` + default permissions)

## Endpoints

- `GET /`
- `GET /health/live`
- `GET /health/ready`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me` (Bearer token required)
- `GET /roles` (Bearer token required if called through gateway)
- `GET /permissions` (Bearer token required if called through gateway)

## JWT claims emitted on login

- `sub`
- `email`
- `roles`
- `scopes`
- `iat`
- `exp`
- `iss`
- `aud`

## Local run

```bash
cd identity-service
source .venv/bin/activate
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --port 8001
```

## Migrations (Alembic)

```bash
cd identity-service
source .venv/bin/activate
alembic -c alembic.ini upgrade head
```
