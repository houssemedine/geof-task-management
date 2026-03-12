from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Permission, Role

DEFAULT_ROLES = ["admin", "member"]
DEFAULT_PERMISSIONS = [
    "task:create",
    "task:read",
    "task:update",
    "task:delete",
    "task:assign",
    "analytics:read",
    "users:manage",
]
MEMBER_PERMISSIONS = ["task:read", "task:create", "task:update"]


def bootstrap_rbac(db: Session) -> None:
    """Initialise les roles et permissions minimaux en base."""
    permissions_by_name = {
        permission.name: permission for permission in db.scalars(select(Permission)).all()
    }

    for permission_name in DEFAULT_PERMISSIONS:
        if permission_name not in permissions_by_name:
            permission = Permission(name=permission_name)
            db.add(permission)
            permissions_by_name[permission_name] = permission

    roles_by_name = {role.name: role for role in db.scalars(select(Role)).all()}
    for role_name in DEFAULT_ROLES:
        if role_name not in roles_by_name:
            role = Role(name=role_name)
            db.add(role)
            roles_by_name[role_name] = role

    db.flush()

    member_role = roles_by_name["member"]
    member_permission_set = {
        permissions_by_name[permission_name] for permission_name in MEMBER_PERMISSIONS
    }
    for permission in member_permission_set:
        if permission not in member_role.permissions:
            member_role.permissions.append(permission)

    admin_role = roles_by_name["admin"]
    for permission in permissions_by_name.values():
        if permission not in admin_role.permissions:
            admin_role.permissions.append(permission)

    db.commit()
