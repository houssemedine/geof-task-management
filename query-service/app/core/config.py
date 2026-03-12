import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    """Lit une variable d'environnement booleenne avec valeur par defaut."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Lit une variable d'environnement entiere avec valeur par defaut."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Modélise la structure "Settings"."""

    service_name: str = os.getenv("SERVICE_NAME", "query-service")
    service_version: str = os.getenv("SERVICE_VERSION", "0.1.0")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./query.db")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "identity-service")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "gf-task-management")
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")
    rabbitmq_exchange: str = os.getenv("RABBITMQ_EXCHANGE", "task.events")
    rabbitmq_queue: str = os.getenv("RABBITMQ_QUEUE", "query.tasks")
    rabbitmq_dlq_queue: str = os.getenv("RABBITMQ_DLQ_QUEUE", "query.tasks.dlq")
    consumer_max_retries: int = _env_int("CONSUMER_MAX_RETRIES", 3)
    enable_event_consumer: bool = _env_bool("ENABLE_EVENT_CONSUMER", False)


settings = Settings()
