from pydantic import BaseModel


class RoleResponse(BaseModel):
    """Modélise la structure "RoleResponse"."""

    id: int
    name: str


class PermissionResponse(BaseModel):
    """Modélise la structure "PermissionResponse"."""

    id: int
    name: str
