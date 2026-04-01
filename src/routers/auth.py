from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.auth import UserToken
from src.schemas.auth import TokenCreate, TokenResponse
from src.services.auth import AuthService
from src.core.config import get_session

auth_router = APIRouter(prefix="/auth")


@auth_router.post("/token", response_model=TokenResponse)
async def save_token(
    body: TokenCreate,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    token = await service.save_token(body.user_id, body.token)
    return TokenResponse(user_id=token.user_id, created_at=token.created_at)


@auth_router.get("/token/{user_id}", response_model=TokenResponse)
async def get_token(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(UserToken).where(UserToken.user_id == user_id)
    )
    token_record = result.scalar_one_or_none()
    if token_record is None:
        raise HTTPException(status_code=404, detail="Token not found")
    return TokenResponse(user_id=token_record.user_id, created_at=token_record.created_at)


@auth_router.delete("/token/{user_id}")
async def delete_token(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    deleted = await service.delete_token(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"status": "deleted"}
