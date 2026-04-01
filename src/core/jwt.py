import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from jose import JWTError, jwt

from src.core import config


def create_access_token(subject: uuid.UUID, extra: dict | None = None) -> str:
    """Create a signed access JWT for the given subject (user id)."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "type": "access",
        "exp": now + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
    """Create a signed refresh JWT. Returns (signed_jwt, jti)."""
    jti = str(uuid.uuid4())
    now = datetime.now(UTC)
    payload = {
        "jti": jti,
        "type": "refresh",
        "exp": now + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    token = jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTP 401 if expired or invalid."""
    try:
        return jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
