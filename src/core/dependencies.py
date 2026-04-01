from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core import config
from src.core.config import get_session
from src.core.jwt import decode_token
from src.models.user import User


async def detect_client_type(x_client_type: str | None = Header(default=None)) -> str:
    """Return 'mobile' if X-Client-Type header equals 'mobile', else 'web'."""
    return "mobile" if x_client_type == "mobile" else "web"


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Extract and validate the access token. Cookie first, then Bearer header."""
    token = request.cookies.get("access_token")

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly auth cookies on the response."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=config.SECURE_COOKIES,
        samesite="lax",
        max_age=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=config.SECURE_COOKIES,
        samesite="lax",
        max_age=config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


ClientType = Annotated[str, Depends(detect_client_type)]
CurrentUser = Annotated[User, Depends(get_current_user)]
