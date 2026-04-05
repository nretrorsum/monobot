import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy import select

from src.core.config import async_session
from src.models.user import User
from src.bot.keyboards import get_main_keyboard

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    tg_id = message.from_user.id
    tg_name = message.from_user.first_name or message.from_user.username or str(tg_id)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == tg_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                name=f"tg_{tg_id}",
                telegram_id=tg_id,
                is_active=True,
                is_superuser=False,
                is_admin=False,
                is_verified=False,
            )
            session.add(user)
            await session.commit()
            logger.info("Created new user from Telegram: tg_id=%s", tg_id)

    keyboard = get_main_keyboard()
    await message.answer(
        f"Привіт, {tg_name}! 👋\n\n"
        "Я — Monobot. Допоможу відстежувати витрати та баланс.\n\n"
        "Команди:\n"
        "/balance — поточний баланс\n"
        "/today — витрати за сьогодні",
        reply_markup=keyboard if keyboard.inline_keyboard else None,
    )
