from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.schemas import HealthLiveResponse, HealthReadyResponse, RootResponse

router = APIRouter()


@router.get("/", response_model=RootResponse)
def root() -> RootResponse:
    """Retourne les informations de base du service."""
    return RootResponse(
        service=settings.service_name,
        version=settings.service_version,
        status="ok",
    )


@router.get("/health/live", response_model=HealthLiveResponse)
def health_live() -> HealthLiveResponse:
    """Retourne l'etat de liveness du service."""
    return HealthLiveResponse(
        service=settings.service_name,
        status="alive",
    )


@router.get("/health/ready", response_model=HealthReadyResponse)
def health_ready() -> HealthReadyResponse:
    """Retourne l'etat de readiness du service."""
    return HealthReadyResponse(
        service=settings.service_name,
        status="ready",
        checked_at=datetime.now(timezone.utc).isoformat(),
    )
