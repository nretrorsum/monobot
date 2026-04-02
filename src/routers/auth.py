import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.auth import TokenCreate, TokenResponse
from src.services.auth import AuthService
from src.core.config import get_session
from src.core.dependencies import CurrentUser

logger = logging.getLogger(__name__)
auth_router = APIRouter(prefix="/auth")


@auth_router.post("/token", response_model=TokenResponse)
async def save_token(
    user: CurrentUser,
    body: TokenCreate,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    try:
        token = await service.save_token(body.user_id, body.token)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return TokenResponse(user_id=token.user_id, created_at=token.created_at)


@auth_router.get("/token/{user_id}", response_model=TokenResponse)
async def get_token(
    user_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        service = AuthService(session)
        token_record = await service.get_token(user_id)
        if token_record is None:
            raise HTTPException(status_code=404, detail="Token not found")
        return TokenResponse(user_id=token_record.user_id, created_at=token_record.created_at)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting token for user %s", user_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@auth_router.delete("/token/{user_id}")
async def delete_token(
    user_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    if user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        service = AuthService(session)
        deleted = await service.delete_token(user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Token not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting token for user %s", user_id)
        raise HTTPException(status_code=500, detail="Internal server error")
