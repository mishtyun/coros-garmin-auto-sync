import asyncio

from aiogram import Bot, Dispatcher

from telegram import handlers
from telegram.configuration import telegram_bot_settings

__all__ = ["run_bot"]


async def app(bot: Bot, dispatcher: Dispatcher):
    dispatcher.include_router(handlers.sport_router)
    dispatcher.include_router(handlers.base_router)
    await dispatcher.start_polling(bot)


def run_bot():
    bot = Bot(token=telegram_bot_settings.token)
    dispatcher = Dispatcher()

    asyncio.run(app(bot=bot, dispatcher=dispatcher))
