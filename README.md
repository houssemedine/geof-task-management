# gf-task-management

Task management backend with 4 FastAPI services:
- identity-service
- task-service
- query-service
- api-gateway

## Architecture summary

- API Gateway is the single entrypoint for clients.
- Identity Service handles authentication and RBAC catalog.
- Task Service is the write-side (source of truth for task mutations).
- Query Service is the read-side (task listing and analytics).
- Task changes are propagated asynchronously through RabbitMQ.

## Run with Docker Compose

```bash
docker compose up --build
```

## Service URLs

- Gateway: `http://localhost:8000`
- Identity: `http://localhost:8001`
- Task: `http://localhost:8002`
- Query: `http://localhost:8003`

## Database Services (PostgreSQL)

- Identity DB: `localhost:5433`
- Task DB: `localhost:5434`
- Query DB: `localhost:5435`

## Message Broker (RabbitMQ)

- AMQP: `localhost:5672`
- Management UI: `http://localhost:15672` (user: `app_user`, password: `app_password`)

## Gateway API surface (what clients should call)

Public:

- `GET /`
- `GET /health/live`
- `GET /health/ready`
- `POST /auth/register`
- `POST /auth/login`

Protected (Bearer token required):

- `GET /auth/me`
- `GET /roles`
- `GET /permissions`
- `POST /tasks`
- `GET /tasks` (served by query-service)
- `GET /tasks/{id}`
- `PUT /tasks/{id}`
- `POST /tasks/{id}/assign`
- `POST /tasks/{id}/status`
- `DELETE /tasks/{id}`
- `GET /analytics/overview`

## Service-level endpoints

Identity Service:

- `GET /`
- `GET /health/live`
- `GET /health/ready`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /roles`
- `GET /permissions`

Task Service:

- `GET /`
- `GET /health/live`
- `GET /health/ready`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{id}`
- `PUT /tasks/{id}`
- `POST /tasks/{id}/assign`
- `POST /tasks/{id}/status`
- `DELETE /tasks/{id}`

Query Service:

- `GET /`
- `GET /health/live`
- `GET /health/ready`
- `GET /tasks?page=1&page_size=20&status=&priority=&assignee=`
- `GET /analytics/overview`

## Tests and Code Quality

Install dependencies in all 4 virtualenvs:

```bash
make install
```

Run endpoint tests for each service:

```bash
make test
```

Run linting:

```bash
make lint
```

Check formatting:

```bash
make format-check
```

Auto-format:

```bash
make format
```

## Migrations

In Docker Compose, each service runs `alembic upgrade head` at startup.
For local service execution, run migrations manually in each service directory before `uvicorn`.

## Implementation Specs

- Identity MVP spec: `docs/identity_service_mvp_spec.md`
- Architecture explanation document: `docs/architecture.md`
