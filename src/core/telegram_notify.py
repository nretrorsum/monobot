import logging

import aiohttp

from src.core.config import BOT_TOKEN
from src.schemas.transaction import StatementItem

logger = logging.getLogger(__name__)

CURRENCY = {
    980: "₴",
    840: "$",
    978: "€",
}

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def _format_amount(kopiykas: int, currency_code: int = 980) -> str:
    symbol = CURRENCY.get(currency_code, "")
    amount = kopiykas / 100
    formatted = f"{amount:,.2f}".replace(",", " ")
    return f"{formatted} {symbol}"


def _build_message(item: StatementItem) -> str:
    is_expense = item.amount < 0
    emoji = "🔴" if is_expense else "🟢"
    direction = "Витрата" if is_expense else "Надходження"

    lines = [
        f"{emoji} <b>{direction}</b>",
        f"  {item.description}",
        f"  Сума: <b>{_format_amount(item.amount, item.currency_code)}</b>",
        f"  Баланс: {_format_amount(item.balance, item.currency_code)}",
    ]

    if item.cashback_amount:
        lines.append(f"  Кешбек: +{_format_amount(item.cashback_amount, item.currency_code)}")

    return "\n".join(lines)


async def notify_transaction(telegram_id: int, item: StatementItem) -> None:
    if not BOT_TOKEN:
        return

    text = _build_message(item)
    payload = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(TELEGRAM_API, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("Telegram notify failed: %s %s", resp.status, body)
    except Exception:
        logger.exception("Failed to send Telegram notification")
