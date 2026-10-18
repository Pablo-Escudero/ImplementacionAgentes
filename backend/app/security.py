"""Hash de contraseñas (bcrypt) y tokens de acceso (JWT)."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

# bcrypt solo procesa los primeros 72 bytes de la contraseña.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Contraseña demasiado larga para bcrypt o hash mal formado.
        return False


def create_access_token(subject: str) -> str:
    """Crea un JWT firmado cuyo `sub` es el id del usuario."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Devuelve el `sub` del token, o None si es inválido o está expirado."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
    except jwt.InvalidTokenError:
        return None
    return payload.get("sub")
