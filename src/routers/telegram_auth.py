import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import BOT_TOKEN, get_session
from src.core.jwt import create_access_token
from src.services.telegram_auth import get_or_create_user, verify_init_data

logger = logging.getLogger(__name__)

telegram_auth_router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramAuthRequest(BaseModel):
    init_data: str


class TelegramAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@telegram_auth_router.post("/telegram", response_model=TelegramAuthResponse)
async def telegram_auth(
    body: TelegramAuthRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TelegramAuthResponse:
    origin = request.headers.get("origin", "unknown")
    logger.info("POST /auth/telegram from origin=%s", origin)

    try:
        user_data = verify_init_data(body.init_data, BOT_TOKEN)
    except HTTPException:
        logger.error("initData verification failed for origin=%s", origin)
        raise

    telegram_id = user_data.get("id")
    if not telegram_id:
        logger.error("No user id in parsed initData: keys=%s", list(user_data.keys()))
        raise HTTPException(status_code=401, detail="No user id in initData")

    user = await get_or_create_user(
        db=session,
        telegram_id=telegram_id,
        first_name=user_data.get("first_name"),
        username=user_data.get("username"),
    )

    access_token = create_access_token(user.id)
    logger.info(
        "Auth successful: user_id=%s, telegram_id=%s",
        user.id,
        telegram_id,
    )

    return TelegramAuthResponse(access_token=access_token)
