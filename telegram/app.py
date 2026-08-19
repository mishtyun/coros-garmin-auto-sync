import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand

from core.configuration import redis_configuration
from telegram import handlers
from telegram.autosync import autosync_loop
from telegram.configuration import telegram_bot_settings

__all__ = ["run_bot"]

BOT_COMMANDS = [
    BotCommand(command="start", description="What this bot does"),
    BotCommand(command="register", description="Link Coros and Garmin accounts"),
    BotCommand(command="sport", description="Open the sync menu"),
    BotCommand(command="plan_workout", description="Plan a workout from text (AI)"),
    BotCommand(command="autosync", description="Automatic sync settings"),
    BotCommand(command="stats", description="Workout stats and digests"),
    BotCommand(command="status", description="Check Coros/Garmin sessions"),
    BotCommand(command="settings", description="Show linked accounts"),
    BotCommand(command="unlink", description="Remove accounts and data"),
    BotCommand(command="cancel", description="Abort registration"),
    BotCommand(command="help", description="List all commands"),
]


async def app(bot: Bot, dispatcher: Dispatcher):
    dispatcher.include_router(handlers.registration_router)
    dispatcher.include_router(handlers.stats_router)
    dispatcher.include_router(handlers.sport_router)
    dispatcher.include_router(handlers.workout_planner_router)
    dispatcher.include_router(handlers.base_router)

    await bot.set_my_commands(BOT_COMMANDS)

    autosync_task = asyncio.create_task(autosync_loop(bot))
    try:
        await dispatcher.start_polling(bot)
    finally:
        autosync_task.cancel()


def run_bot():
    bot = Bot(token=telegram_bot_settings.token)
    storage = RedisStorage.from_url(redis_configuration.get_url())
    dispatcher = Dispatcher(storage=storage)

    asyncio.run(app(bot=bot, dispatcher=dispatcher))
