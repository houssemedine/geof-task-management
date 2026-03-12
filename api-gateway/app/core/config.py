import os
from dataclasses import dataclass


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

    service_name: str = os.getenv("SERVICE_NAME", "api-gateway")
    service_version: str = os.getenv("SERVICE_VERSION", "0.1.0")

    identity_service_url: str = os.getenv("IDENTITY_SERVICE_URL", "http://localhost:8001")
    task_service_url: str = os.getenv("TASK_SERVICE_URL", "http://localhost:8002")
    query_service_url: str = os.getenv("QUERY_SERVICE_URL", "http://localhost:8003")

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "identity-service")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "gf-task-management")

    rate_limit_requests_per_minute: int = _env_int("RATE_LIMIT_REQUESTS_PER_MINUTE", 120)
    upstream_timeout_seconds: int = _env_int("UPSTREAM_TIMEOUT_SECONDS", 15)


settings = Settings()
