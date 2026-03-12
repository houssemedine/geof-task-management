from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Recupere l'utilisateur courant depuis le JWT."""
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise UNAUTHORIZED

    user = db.scalar(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    if user is None:
        raise UNAUTHORIZED
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return user
