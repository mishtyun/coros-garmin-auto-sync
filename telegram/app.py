import asyncio
from aiogram import Bot, Dispatcher, types, F

from coros.services import AuthService
from coros.services.activity import ActivityService
from telegram.configuration import telegram_bot_settings

dispatcher = Dispatcher()


@dispatcher.message(F.text == "Download latest activity")
async def download_latest_activity_handler(message: types.Message):
    await message.reply("processing...")

    from coros.configuration import coros_configuration

    AuthService(coros_configuration).get_access_token()
    file_path = ActivityService(coros_configuration).download_latest_activity()

    latest_activity_file = types.FSInputFile(file_path)
    await message.reply_document(caption="Downloaded", document=latest_activity_file)


@dispatcher.message()
async def cmd_start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="Download latest activity")],
        [types.KeyboardButton(text="...")],
    ]

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="What i need to do ...",
    )

    await message.answer("Action ?", reply_markup=keyboard)


async def app():
    bot = Bot(token=telegram_bot_settings.token)
    await dispatcher.start_polling(bot)


def run_bot():
    asyncio.run(app())


if __name__ == "__main__":
    run_bot()
