import asyncio
from time import sleep

from aiogram import Bot, Dispatcher, types, F

from coros.models import DateActivityFilter
from coros.services import AuthService
from coros.services.activity import ActivityService
from garmin_connect.app import init_api
from telegram.configuration import telegram_bot_settings

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

        garmin_api.upload_activity(file_path)

        sleep(3)

        latest_activity = garmin_api.get_last_activity()
        activity_id = latest_activity.get("activityId")

        garmin_api.change_activity_visibility(activity_id, "public")

        garmin_activity_link = (
            f"https://connect.garmin.com/modern/activity/{activity_id}"
        )
        await message.answer(
            f"Synced successfully\nActivity link {garmin_activity_link}"
        )
    except Exception as e:
        await message.answer("Error while syncing")
        raise e


@dispatcher.message(F.text == "Sync all daily activities")
async def sync_all__daily_activities_button_handler(message: types.Message):
    kb = [
        [
            types.InlineKeyboardButton(
                text="Choose the date", callback_data="choose_date"
            )
        ],
        [types.InlineKeyboardButton(text="Yesterday", callback_data="yesterday")],
        [types.InlineKeyboardButton(text="Today", callback_data="today")],
    ]

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)

    await message.reply("When", reply_markup=keyboard)


@dispatcher.callback_query()
async def process_callback_button1(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Нажата первая кнопка!")


async def sync_all_activity_by_dates_handler(start_date: str, end_date: str) -> str:
    from coros.configuration import coros_configuration

    AuthService(coros_configuration).get_access_token()
    file_path = ActivityService(coros_configuration).download_daily_activities(
        DateActivityFilter(start_date=start_date, end_date=end_date)
    )

    # response = []
    # garmin_activity_link = (
    #     f"https://connect.garmin.com/modern/activity/{activity_id}"
    # )


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
