from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_session
from src.core.dependencies import ClientType, CurrentUser, set_auth_cookies
from src.core.jwt import decode_token
from src.models.user import User
from src.schemas.jwt_auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from src.services.jwt_auth import (
    authenticate_user,
    create_token_pair,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)

jwt_auth_router = APIRouter()


@jwt_auth_router.post("/register")
async def register(
    data: RegisterRequest,
    response: Response,
    client_type: ClientType,
    db: AsyncSession = Depends(get_session),
) -> TokenResponse | UserOut:
    """Register a new user and return tokens."""
    user = await register_user(db, data)
    access_token, refresh_token = await create_token_pair(db, user.id, client_type)

    if client_type == "mobile":
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    set_auth_cookies(response, access_token, refresh_token)
    return UserOut.model_validate(user)


@jwt_auth_router.post("/login")
async def login(
    data: LoginRequest,
    response: Response,
    client_type: ClientType,
    db: AsyncSession = Depends(get_session),
) -> TokenResponse | UserOut:
    """Authenticate user and return tokens."""
    user = await authenticate_user(db, data.email, data.password)
    access_token, refresh_token = await create_token_pair(db, user.id, client_type)

    if client_type == "mobile":
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    set_auth_cookies(response, access_token, refresh_token)
    return UserOut.model_validate(user)


@jwt_auth_router.post("/refresh")
async def refresh_tokens(
    request: Request,
    response: Response,
    client_type: ClientType,
    db: AsyncSession = Depends(get_session),
    body: RefreshRequest | None = None,
) -> TokenResponse | UserOut:
    """Refresh the token pair using the refresh token."""
    if client_type == "mobile" and body:
        old_refresh = body.refresh_token
    else:
        old_refresh = request.cookies.get("refresh_token")

    if not old_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not provided",
        )

    access_token, refresh_token = await rotate_refresh_token(db, old_refresh, client_type)

    if client_type == "mobile":
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    set_auth_cookies(response, access_token, refresh_token)
    payload = decode_token(access_token)
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one()
    return UserOut.model_validate(user)


@jwt_auth_router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: CurrentUser,
    client_type: ClientType,
    db: AsyncSession = Depends(get_session),
    body: RefreshRequest | None = None,
) -> dict:
    """Revoke refresh token and clear cookies."""
    if client_type == "mobile" and body:
        refresh_jwt = body.refresh_token
    else:
        refresh_jwt = request.cookies.get("refresh_token")

    if refresh_jwt:
        await revoke_refresh_token(db, refresh_jwt)

    if client_type == "web":
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

    return {"detail": "logged out"}


@jwt_auth_router.get("/me")
async def me(current_user: CurrentUser) -> UserOut:
    """Return current authenticated user."""
    return UserOut.model_validate(current_user)
