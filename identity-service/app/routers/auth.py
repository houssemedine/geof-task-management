from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.bootstrap import bootstrap_rbac
from app.core.db import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Role, User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(tags=["auth"])


def _to_user_response(user: User) -> UserResponse:
    """Convertit le modele User vers le schema de reponse API."""
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        roles=sorted({role.name for role in user.roles}),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    """Cree un nouvel utilisateur si l'email n'existe pas deja."""
    existing_user = db.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    member_role = db.scalar(select(Role).where(Role.name == "member"))
    if member_role is None:
        bootstrap_rbac(db)
        member_role = db.scalar(select(Role).where(Role.name == "member"))

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    if member_role is not None:
        user.roles.append(member_role)

    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(user, attribute_names=["roles"])

    return _to_user_response(user)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authentifie un utilisateur et retourne un token JWT."""
    user = db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.email == payload.email)
    )

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    roles = sorted({role.name for role in user.roles})
    scopes = sorted({permission.name for role in user.roles for permission in role.permissions})

    token, expires_in = create_access_token(
        user_id=user.id,
        email=user.email,
        roles=roles,
        scopes=scopes,
    )

    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Retourne le profil de l'utilisateur authentifie."""
    return _to_user_response(current_user)
