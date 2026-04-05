import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from src.core.config import async_session
from src.models.user import User
from src.services.balance import BalanceService

logger = logging.getLogger(__name__)

router = Router()

CURRENCY = {
    980: ("UAH", "₴"),
    840: ("USD", "$"),
    978: ("EUR", "€"),
}


def format_money(kopiykas: int, currency_code: int = 980) -> str:
    symbol = CURRENCY.get(currency_code, ("", ""))[1]
    amount = kopiykas / 100
    formatted = f"{amount:,.2f}".replace(",", " ")
    return f"{formatted} {symbol}"


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
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
        balances = await service.get_user_balances(user.id)

    if not balances:
        await message.answer("Рахунки ще не підключені. Прив'яжи Monobank токен.")
        return

    lines = ["💰 <b>Баланс рахунків:</b>\n"]
    for acc in balances:
        name = acc.display_name or acc.account_id[:8]
        lines.append(f"  {name}: <b>{format_money(acc.balance, acc.currency_code)}</b>")

    await message.answer("\n".join(lines), parse_mode="HTML")
