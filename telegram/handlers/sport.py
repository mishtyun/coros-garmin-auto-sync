from datetime import datetime, timedelta

from aiogram import types, F, Router

from coros import coros_configuration
from coros.services import AuthService, ActivityService
from garmin_connect.app import init_api
from telegram.enums import DailyActivitiesDateTypes
from telegram.keyboards import get_activities_dates_keyboard
from telegram.utils import upload_and_get_url, get_activity_url


__all__ = ["router"]


START_HANDLER_COMMAND = "/sport"

router = Router()
garmin_api = init_api()


@router.message(F.text == "Download latest activity")
async def download_latest_activity_button_handler(message: types.Message):
    try:
        AuthService(coros_configuration).get_access_token()
        file_path = ActivityService(coros_configuration).download_latest_activity()

        latest_activity_file = types.FSInputFile(file_path)
        await message.reply_document(document=latest_activity_file)
    except Exception as e:
        await message.answer("Error while downloading")
        raise e


@router.message(F.text == "Sync latest activity")
async def sync_latest_activity_button_handler(message: types.Message):
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


@router.message(F.text == "Sync all daily activities")
async def sync_all_daily_activities_button_handler(message: types.Message):
    keyboard = get_activities_dates_keyboard(callback_data_prefix="sync")
    await message.reply("When", reply_markup=keyboard)


@router.message(F.text == "Get daily activities")
async def get_all_daily_activities_button_handler(message: types.Message):
    keyboard = get_activities_dates_keyboard(callback_data_prefix="get")
    await message.reply("When", reply_markup=keyboard)


@router.callback_query(F.data.startswith("sync"))
async def process_sync_callback_button(callback_query: types.CallbackQuery):
    from telegram.utils import sync_all_activity_by_dates_handler

    choice = callback_query.data

    date_format = "%Y%m%d"
    start_day = end_date = None

    if choice.endswith(DailyActivitiesDateTypes.yesterday.value):
        start_day = end_date = (datetime.now() - timedelta(1)).strftime(date_format)
    elif choice.endswith(DailyActivitiesDateTypes.today.value):
        start_day = end_date = datetime.now().strftime(date_format)

    if not start_day or not end_date:
        return await callback_query.message.answer("Invalid dates")

    message_to_send = await sync_all_activity_by_dates_handler(
        garmin_api, start_day, end_date
    )
    await callback_query.message.answer(message_to_send)


@router.callback_query(F.data.startswith("get"))
async def process_get_callback_button(callback_query: types.CallbackQuery):
    choice = callback_query.data

    date_format = "%Y-%m-%d"
    start_day = end_date = None

    if choice.endswith(DailyActivitiesDateTypes.yesterday.value):
        start_day = end_date = (datetime.now() - timedelta(1)).strftime(date_format)
    elif choice.endswith(DailyActivitiesDateTypes.today.value):
        start_day = end_date = datetime.now().strftime(date_format)

    if not start_day or not end_date:
        return await callback_query.message.answer("Invalid dates")

    activities = garmin_api.get_activities_by_date(
        startdate=start_day, enddate=end_date
    )

    message_to_send = ""
    for activity in activities:
        activity_url = get_activity_url(activity["activityId"])
        message_to_send += f"{activity['activityName']}: {activity_url}\n"

    await callback_query.message.answer(
        message_to_send if message_to_send else "No activities",
    )


@router.message(F.text == START_HANDLER_COMMAND)
async def sport_cmd_start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="Download latest activity")],
        [types.KeyboardButton(text="Sync latest activity")],
        [types.KeyboardButton(text="Sync all daily activities")],
        [types.KeyboardButton(text="Get daily activities")],
    ]

    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer("Action ?", reply_markup=keyboard)
