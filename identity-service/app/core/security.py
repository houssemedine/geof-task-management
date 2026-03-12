import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.core.config import settings

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Hash le mot de passe avant stockage."""
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifie qu'un mot de passe correspond au hash en base."""
    try:
        scheme, iterations, salt_b64, digest_b64 = password_hash.split("$", maxsplit=3)
        if scheme != "pbkdf2_sha256":
            return False
    except ValueError:
        return False

    computed_digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        plain_password.encode("utf-8"),
        base64.b64decode(salt_b64.encode("ascii")),
        int(iterations),
    )
    provided_digest = base64.b64decode(digest_b64.encode("ascii"))
    return hmac.compare_digest(computed_digest, provided_digest)


def create_access_token(
    user_id: int,
    email: str,
    roles: list[str],
    scopes: list[str],
) -> tuple[str, int]:
    """Genere un JWT d'acces pour l'utilisateur authentifie."""
    issued_at = datetime.now(UTC)
    expires_in = settings.jwt_access_token_expires_seconds
    expires_at = issued_at + timedelta(seconds=expires_in)

    payload = {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "scopes": scopes,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }

    token = jwt.encode(
        claims=payload,
        key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return token, expires_in


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
