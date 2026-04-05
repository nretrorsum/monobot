import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qs

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User

logger = logging.getLogger(__name__)


def verify_init_data(init_data: str, bot_token: str) -> dict:
    """Verify Telegram Mini App initData and return parsed user data.

    Follows Telegram's validation algorithm:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    logger.info("Verifying initData (length=%d)", len(init_data))
    parsed = parse_qs(init_data, keep_blank_values=True)
    logger.debug("Parsed initData keys: %s", list(parsed.keys()))

    if "hash" not in parsed:
        logger.warning("initData missing hash parameter")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing hash in initData",
        )

    received_hash = parsed.pop("hash")[0]

    # Build data-check-string: sorted key=value pairs joined by \n
    data_check_string = "\n".join(
        f"{k}={v[0]}" for k, v in sorted(parsed.items())
    )

    # secret_key = HMAC-SHA256(bot_token, "WebAppData")
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()

    # calculated_hash = HMAC-SHA256(secret_key, data_check_string)
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        logger.warning(
            "initData signature mismatch: received=%s, calculated=%s",
            received_hash[:8] + "...",
            calculated_hash[:8] + "...",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid initData signature",
        )

    logger.info("initData signature verified successfully")

    # Parse user JSON
    user_data = {}
    if "user" in parsed:
        user_data = json.loads(parsed["user"][0])
        logger.info(
            "Parsed user: telegram_id=%s, username=%s",
            user_data.get("id"),
            user_data.get("username"),
        )
    else:
        logger.warning("initData contains no 'user' field")

    return user_data


async def get_or_create_user(
    db: AsyncSession,
    telegram_id: int,
    first_name: str | None = None,
    username: str | None = None,
) -> User:
    """Find existing user by telegram_id or create a new one."""
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if user:
        logger.info("Found existing user: id=%s, telegram_id=%s", user.id, telegram_id)
        return user

    name = first_name or username or f"tg_{telegram_id}"
    logger.info("Creating new user: name=%s, telegram_id=%s", name, telegram_id)
    user = User(
        name=f"tg_{telegram_id}",
        telegram_id=telegram_id,
        is_active=True,
        is_superuser=False,
        is_admin=False,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Created user: id=%s, telegram_id=%s", user.id, telegram_id)
    return user
