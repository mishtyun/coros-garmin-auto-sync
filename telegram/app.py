import asyncio
from aiogram import Bot, Dispatcher, types, F

from coros.services import AuthService
from coros.services.activity import ActivityService
from garminconnect.app import init_api
from telegram.configuration import telegram_bot_settings

dispatcher = Dispatcher()


@dispatcher.message(F.text == "Download latest activity")
async def download_latest_activity_handler(message: types.Message):
    from coros.configuration import coros_configuration

    try:
        AuthService(coros_configuration).get_access_token()
        file_path = ActivityService(coros_configuration).download_latest_activity()

        latest_activity_file = types.FSInputFile(file_path)
        await message.reply_document(document=latest_activity_file)
    except Exception as e:
        await message.answer("Error while downloading")
        raise e


@dispatcher.message(F.text == "Sync latest activity")
async def sync_latest_activity_handler(message: types.Message):
    from coros.configuration import coros_configuration

    try:
        AuthService(coros_configuration).get_access_token()
        file_path = ActivityService(coros_configuration).download_latest_activity()

        api = init_api()
        api.upload_activity(file_path)
    except Exception as e:
        await message.answer("Error while syncing")
        raise e


@dispatcher.message()
async def cmd_start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="Download latest activity")],
        [types.KeyboardButton(text="Sync latest activity")],
    ]

    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer("Action ?", reply_markup=keyboard)


async def app():
    bot = Bot(token=telegram_bot_settings.token)
    await dispatcher.start_polling(bot)


def run_bot():
    asyncio.run(app())


if __name__ == "__main__":
    run_bot()
