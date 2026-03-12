from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Permission, Role
from app.schemas import PermissionResponse, RoleResponse

router = APIRouter(tags=["rbac"])


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(db: Session = Depends(get_db)) -> list[RoleResponse]:
    """Liste tous les roles disponibles."""
    roles = db.scalars(select(Role).order_by(Role.name.asc())).all()
    return [RoleResponse(id=role.id, name=role.name) for role in roles]


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(db: Session = Depends(get_db)) -> list[PermissionResponse]:
    """Liste toutes les permissions disponibles."""
    permissions = db.scalars(select(Permission).order_by(Permission.name.asc())).all()
    return [
        PermissionResponse(id=permission.id, name=permission.name) for permission in permissions
    ]
