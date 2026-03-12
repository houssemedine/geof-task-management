from pydantic import BaseModel


class RootResponse(BaseModel):
    """Modélise la structure "RootResponse"."""

    service: str
    version: str
    status: str


class HealthLiveResponse(BaseModel):
    """Modélise la structure "HealthLiveResponse"."""

    service: str
    status: str


class HealthReadyResponse(BaseModel):
    """Modélise la structure "HealthReadyResponse"."""

    service: str
    status: str
    checked_at: str
