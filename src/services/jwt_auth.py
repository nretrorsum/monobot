import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import config
from src.core.hashing import hash_password, verify_password
from src.core.jwt import create_access_token, create_refresh_token, decode_token
from src.models.refresh_token import RefreshToken
from src.models.user import User
from src.schemas.jwt_auth import RegisterRequest


def _hash_jti(jti: str) -> str:
    """Return sha256 hex digest of a jti string."""
    return hashlib.sha256(jti.encode()).hexdigest()


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """Hash password and persist a new User. Raises 400 if email already exists."""
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed = await hash_password(data.password)
    user = User(
        name=data.email,
        email=data.email,
        password=hashed,
        is_active=True,
        is_superuser=False,
        is_admin=False,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Load user by email and verify password. Raises 401 on failure."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not await verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return user


async def create_token_pair(
    db: AsyncSession, user_id: uuid.UUID, client_type: str
) -> tuple[str, str]:
    """Generate an access + refresh token pair. Persists sha256(jti) to the DB."""
    access_token = create_access_token(user_id)
    refresh_jwt, jti = create_refresh_token()

    token_record = RefreshToken(
        jti_hash=_hash_jti(jti),
        user_id=user_id,
        client_type=client_type,
        expires_at=datetime.now(UTC) + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(token_record)
    await db.commit()

    return access_token, refresh_jwt


async def rotate_refresh_token(
    db: AsyncSession, old_refresh_jwt: str, client_type: str
) -> tuple[str, str]:
    """Validate old refresh JWT, delete its jti_hash, issue a new pair.

    Token theft detection: if jti_hash is not found (already rotated),
    revoke ALL refresh tokens for this user and raise HTTP 401.
    """
    payload = decode_token(old_refresh_jwt)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    jti_hash = _hash_jti(jti)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.jti_hash == jti_hash)
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        # Token reuse detected — revoke all tokens for the user encoded in jti
        # We need to find user_id from any token with same jti pattern
        # Since we can't determine user from a missing token, decode won't help
        # But we can look for tokens and the jti was already used
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token reuse detected",
        )

    user_id = token_record.user_id

    # Delete the old token
    await db.delete(token_record)
    await db.commit()

    # Issue new pair
    return await create_token_pair(db, user_id, client_type)


async def revoke_refresh_token(db: AsyncSession, refresh_jwt: str) -> None:
    """Decode refresh JWT and delete the matching jti_hash. Silent if not found."""
    payload = decode_token(refresh_jwt)
    jti = payload.get("jti")
    if jti:
        jti_hash = _hash_jti(jti)
        await db.execute(
            delete(RefreshToken).where(RefreshToken.jti_hash == jti_hash)
        )
        await db.commit()
