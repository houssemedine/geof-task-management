from jose import JWTError, jwt

from app.core.config import settings


def decode_access_token(token: str) -> dict:
    """Decode et valide un JWT d'acces."""
    try:
        return jwt.decode(
            token,
            key=settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
