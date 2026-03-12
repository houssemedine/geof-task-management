from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    """Recupere le payload JWT de la requete courante."""
    try:
        return decode_access_token(token)
    except ValueError:
        raise UNAUTHORIZED


def require_scopes(required_scopes: list[str]) -> Callable:
    """Construit une dependance qui valide les scopes requis."""

    def dependency(token_payload: dict = Depends(get_token_payload)) -> dict:
        """Verifie que le token contient les scopes attendus."""
        token_scopes = token_payload.get("scopes")
        if not isinstance(token_scopes, list):
            raise UNAUTHORIZED

        missing_scopes = [scope for scope in required_scopes if scope not in token_scopes]
        if missing_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {missing_scopes[0]}",
            )

        return token_payload

    return dependency
