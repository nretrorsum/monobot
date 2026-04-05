import logging

from aiogram import Bot, Dispatcher

from src.core.config import BOT_TOKEN
from src.bot.handlers import start, balance, today

logger = logging.getLogger(__name__)


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_routers(start.router, balance.router, today.router)
    return bot, dp
