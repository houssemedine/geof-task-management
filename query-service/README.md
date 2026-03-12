# Query Service

FastAPI service bootstrap.

Endpoints:
- `GET /`
- `GET /health/live`
- `GET /health/ready`
- `GET /tasks?page=1&page_size=20&status=&priority=&assignee=` (requires Bearer token with `task:read`)
- `GET /analytics/overview` (requires Bearer token with `analytics:read`)

RabbitMQ consumer:
- Consumes `task.created`, `task.updated`, `task.assigned`, `task.status_changed`, `task.deleted`
- Projects events into `tasks_read_model` with idempotence (`processed_events` by `event_id`)
- Retries failed messages and moves poison messages to DLQ
- Controlled via `ENABLE_EVENT_CONSUMER` (default: `false`)

Run locally:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8003
```

## Migrations (Alembic)

Run migrations before starting the service in environments that do not auto-create schema:

```bash
cd query-service
source .venv/bin/activate
alembic -c alembic.ini upgrade head
```
