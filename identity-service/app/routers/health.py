from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    """Retourne les informations de base du service."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "ok",
    }


@router.get("/health/live")
def health_live() -> dict[str, str]:
    """Retourne l'etat de liveness du service."""
    return {
        "service": settings.service_name,
        "status": "alive",
    }


@router.get("/health/ready")
def health_ready() -> dict[str, str]:
    """Retourne l'etat de readiness du service."""
    return {
        "service": settings.service_name,
        "status": "ready",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
