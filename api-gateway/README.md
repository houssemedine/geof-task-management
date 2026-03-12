# API Gateway

FastAPI API Gateway.

Responsibilities:
- Route requests to Identity/Task/Query services
- Centralized JWT validation
- `X-Correlation-Id` propagation
- Basic in-memory rate limiting

## Public endpoints (no JWT)

- `GET /`
- `GET /health/live`
- `GET /health/ready`
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh` (route forwarded if implemented by identity-service)

## Routing rules

- `/auth/*`, `/roles`, `/permissions` -> `identity-service`
- `GET /tasks` -> `query-service`
- `/analytics/*` -> `query-service`
- Other `/tasks*` methods (`POST`, `PUT`, `PATCH`, `DELETE`, ...) -> `task-service`

## Protected by gateway JWT check

Every endpoint not listed in public endpoints is protected by Bearer JWT validation.

## Gateway behavior

- Adds or propagates `X-Correlation-Id` on each request/response
- Strips hop-by-hop headers when proxying
- Returns `401` for missing/invalid token on protected routes
- Returns `429` when rate limit is exceeded
- Returns `502` when upstream service is unavailable

Local run:

```bash
cd api-gateway
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```
