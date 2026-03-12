# Task Service

FastAPI write-side service for task lifecycle.

Endpoints:
- `GET /`
- `GET /health/live`
- `GET /health/ready`
- `POST /tasks` (requires `task:create`)
- `GET /tasks` (requires `task:read`)
- `GET /tasks/{id}` (requires `task:read`)
- `PUT /tasks/{id}` (requires `task:update`)
- `POST /tasks/{id}/assign` (requires `task:assign`)
- `POST /tasks/{id}/status` (requires `task:update`)
- `DELETE /tasks/{id}` (requires `task:delete`)

Outbox:
- Domain events are written to `outbox_events` in the same transaction as task writes.
- Background publisher retries failed publications with backoff and marks permanent failures.

Run locally:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8002
```

## Migrations (Alembic)

Run migrations before starting the service in environments that do not auto-create schema:

```bash
cd task-service
source .venv/bin/activate
alembic -c alembic.ini upgrade head
```
