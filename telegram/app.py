import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F

from coros.services import AuthService
from coros.services.activity import ActivityService
from garmin_connect.app import init_api
from telegram.configuration import telegram_bot_settings
from telegram.enums import DailyActivitiesTypes
from telegram.utils import upload_and_get_url

bot = Bot(token=telegram_bot_settings.token)
dispatcher = Dispatcher()

garmin_api = init_api()


@dispatcher.message(F.text == "Download latest activity")
async def download_latest_activity_button_handler(message: types.Message):
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
async def sync_latest_activity_button_handler(message: types.Message):
    from coros.configuration import coros_configuration

    try:
        AuthService(coros_configuration).get_access_token()
        file_path = ActivityService(coros_configuration).download_latest_activity()

        garmin_activity_link = await upload_and_get_url(garmin_api, file_path)

        await message.answer(
            f"Synced successfully\nActivity link {garmin_activity_link}"
        )
    except Exception as e:
        await message.answer("Error while syncing")
        raise e


@dispatcher.message(F.text == "Sync all daily activities")
async def sync_all_daily_activities_button_handler(message: types.Message):
    kb = [
        # [
        #     types.InlineKeyboardButton(
        #         text="Choose the date",
        #         callback_data=DailyActivitiesTypes.choose_date.value,
        #     )
        # ],
        [
            types.InlineKeyboardButton(
                text="Yesterday", callback_data=DailyActivitiesTypes.yesterday.value
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Today", callback_data=DailyActivitiesTypes.today.value
            )
        ],
    ]

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)

    await message.reply("When", reply_markup=keyboard)


@dispatcher.callback_query()
async def process_callback_button1(callback_query: types.CallbackQuery):
    from telegram.utils import sync_all_activity_by_dates_handler

    await bot.answer_callback_query(callback_query.id)

    choice = callback_query.data

    date_format = "%Y%m%d"
    start_day = end_date = None

    match choice:
        case DailyActivitiesTypes.yesterday.value:
            start_day = end_date = (datetime.now() - timedelta(1)).strftime(date_format)
        case DailyActivitiesTypes.today.value:
            start_day = end_date = datetime.now().strftime(date_format)

    message_to_send = await sync_all_activity_by_dates_handler(
        garmin_api, start_day, end_date
    )
    await bot.send_message(callback_query.from_user.id, message_to_send)


@dispatcher.message()
async def cmd_start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="Download latest activity")],
        [types.KeyboardButton(text="Sync latest activity")],
        [types.KeyboardButton(text="Sync all daily activities")],
    ]

    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer("Action ?", reply_markup=keyboard)


async def app():
    await dispatcher.start_polling(bot)


def run_bot():
    asyncio.run(app())


if __name__ == "__main__":
    run_bot()
