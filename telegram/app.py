import asyncio

from aiogram import Bot, Dispatcher

from telegram.configuration import telegram_bot_settings

bot = Bot(token=telegram_bot_settings.token)
dispatcher = Dispatcher()


async def app():
    from handlers import sport_router

    dispatcher.include_router(sport_router)

    await dispatcher.start_polling(bot)


def run_bot():
    asyncio.run(app())


if __name__ == "__main__":
    run_bot()
