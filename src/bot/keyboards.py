from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from src.core.config import TMA_URL


def get_main_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    if TMA_URL:
        buttons.append([
            InlineKeyboardButton(
                text="📊 Відкрити дашборд",
                web_app=WebAppInfo(url=TMA_URL),
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
