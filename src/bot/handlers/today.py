import calendar
import logging
from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from src.core.config import async_session
from src.models.user import User
from src.services.balance import BalanceService
from src.bot.handlers.balance import format_money

logger = logging.getLogger(__name__)

router = Router()


def _date_to_timestamp(d: date) -> int:
    return int(calendar.timegm(d.timetuple()))


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    tg_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == tg_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("Спочатку натисни /start для реєстрації.")
            return

        service = BalanceService(session)
        today_date = date.today()
        from_ts = _date_to_timestamp(today_date)
        to_ts = from_ts + 86400
        income_expenses = await service.get_income_vs_expenses(
            user_id=user.id,
            from_timestamp=from_ts,
            to_timestamp=to_ts,
        )

    lines = [
        f"📅 <b>Сьогодні ({today_date.strftime('%d.%m.%Y')}):</b>\n",
        f"  Витрати: <b>{format_money(income_expenses.total_expenses)}</b>",
        f"  Доходи: <b>{format_money(income_expenses.total_income)}</b>",
    ]

    if income_expenses.net_savings != 0:
        sign = "+" if income_expenses.net_savings > 0 else ""
        lines.append(f"  Нетто: <b>{sign}{format_money(income_expenses.net_savings)}</b>")

    await message.answer("\n".join(lines), parse_mode="HTML")
