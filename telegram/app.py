import asyncio

from aiogram import Bot, Dispatcher

import handlers
from telegram.configuration import telegram_bot_settings

bot = Bot(token=telegram_bot_settings.token)
dispatcher = Dispatcher()


async def app():
    dispatcher.include_router(handlers.sport_router)
    dispatcher.include_router(handlers.base_router)
    await dispatcher.start_polling(bot)


def run_bot():
    asyncio.run(app())


if __name__ == "__main__":
    run_bot()
