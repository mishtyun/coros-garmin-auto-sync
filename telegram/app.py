import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from core.configuration import redis_configuration
from telegram import handlers
from telegram.configuration import telegram_bot_settings

__all__ = ["run_bot"]


async def app(bot: Bot, dispatcher: Dispatcher):
    dispatcher.include_router(handlers.registration_router)
    dispatcher.include_router(handlers.sport_router)
    dispatcher.include_router(handlers.base_router)
    await dispatcher.start_polling(bot)


def run_bot():
    bot = Bot(token=telegram_bot_settings.token)
    storage = RedisStorage.from_url(redis_configuration.get_url())
    dispatcher = Dispatcher(storage=storage)

    asyncio.run(app(bot=bot, dispatcher=dispatcher))
