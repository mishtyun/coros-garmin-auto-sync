import logging
from datetime import datetime, timedelta

from aiogram import types, F, Router

from coros import coros_configuration
from coros.services import AuthService, ActivityService
from garmin.core import get_garmin_api
from telegram.enums import DailyActivitiesDateTypes
from telegram.keyboards import get_activities_dates_keyboard
from telegram.utils import upload_and_get_url, get_activities_message

logger = logging.getLogger(__name__)

__all__ = ["router"]

START_HANDLER_COMMAND = "/sport"

router = Router()
garmin_api = get_garmin_api()


@router.message(F.text == "Download latest activity")
async def download_latest_activity_button_handler(message: types.Message):
    logger.info("Downloading latest activity")
    try:
        AuthService(coros_configuration).get_access_token()
        file_path = ActivityService(coros_configuration).download_latest_activity()

        latest_activity_file = types.FSInputFile(file_path)
        await message.reply_document(document=latest_activity_file)
        logger.info(f"Successfully downloaded and sent latest activity: {file_path}")
    except Exception as e:
        logger.error(
            f"Error while downloading latest activity: {str(e)}", exc_info=True
        )
        await message.answer("Error while downloading")


@router.message(F.text == "Sync latest activity")
async def sync_latest_activity_button_handler(message: types.Message):
    logger.info("Syncing latest activity")
    try:
        AuthService(coros_configuration).get_access_token()
        file_path = ActivityService(coros_configuration).download_latest_activity()

        garmin_activity_link = await upload_and_get_url(garmin_api, file_path)

        await message.answer(
            f"Synced successfully\nActivity link {garmin_activity_link}"
        )
        logger.info(f"Successfully synced latest activity: {garmin_activity_link}")
    except Exception as e:
        logger.error(f"Error while syncing latest activity: {str(e)}", exc_info=True)
        await message.answer("Error while syncing")


@router.message(F.text == "Sync all daily activities")
async def sync_all_daily_activities_button_handler(message: types.Message):
    logger.info("Preparing to sync all daily activities")
    keyboard = get_activities_dates_keyboard(callback_data_prefix="sync")
    await message.reply("When", reply_markup=keyboard)
    logger.info("Sent date selection keyboard for syncing all daily activities")


@router.message(F.text == "Get daily activities")
async def get_all_daily_activities_button_handler(message: types.Message):
    logger.info("Preparing to get all daily activities")
    keyboard = get_activities_dates_keyboard(callback_data_prefix="get")
    await message.reply("When", reply_markup=keyboard)
    logger.info("Sent date selection keyboard for getting all daily activities")


@router.callback_query(F.data.startswith("sync"))
async def process_sync_callback_button(callback_query: types.CallbackQuery):
    logger.info(f"Processing sync callback: {callback_query.data}")
    from telegram.utils import sync_all_activity_by_dates_handler

    choice = callback_query.data

    date_format, coros_date_format = "%Y-%m-%d", "%Y%m%d"
    start_day = end_date = None

    if choice.endswith(DailyActivitiesDateTypes.yesterday.value):
        start_day = end_date = datetime.now() - timedelta(1)
    elif choice.endswith(DailyActivitiesDateTypes.today.value):
        start_day = end_date = datetime.now()

    if not start_day or not end_date:
        logger.warning("Invalid dates for sync")
        return await callback_query.message.answer("Invalid dates")

    logger.info(f"Syncing activities for date range: {start_day} to {end_date}")
    await sync_all_activity_by_dates_handler(
        garmin_api,
        start_day.strftime(coros_date_format),
        end_date.strftime(coros_date_format),
    )

    activities = garmin_api.get_activities_by_date(
        start_date=start_day.strftime(date_format),
        end_date=end_date.strftime(date_format),
    )
    message_to_send = get_activities_message(activities)

    await callback_query.message.answer(message_to_send)
    logger.info(
        f"Sync completed and message sent for date range: {start_day} to {end_date}"
    )


@router.callback_query(F.data.startswith("get"))
async def process_get_callback_button(callback_query: types.CallbackQuery):
    logger.info(f"Processing get callback: {callback_query.data}")
    choice = callback_query.data

    date_format = "%Y-%m-%d"
    start_day = end_date = None

    if choice.endswith(DailyActivitiesDateTypes.yesterday.value):
        start_day = end_date = (datetime.now() - timedelta(1)).strftime(date_format)
    elif choice.endswith(DailyActivitiesDateTypes.today.value):
        start_day = end_date = datetime.now().strftime(date_format)

    if not start_day or not end_date:
        logger.warning("Invalid dates for get")
        return await callback_query.message.answer("Invalid dates")

    logger.info(f"Getting activities for date range: {start_day} to {end_date}")
    activities = garmin_api.get_activities_by_date(
        start_date=start_day, end_date=end_date
    )
    message_to_send = get_activities_message(activities)

    await callback_query.message.answer(message_to_send)
    logger.info(
        f"Activities retrieved and message sent for date range: {start_day} to {end_date}"
    )


@router.message(F.text == START_HANDLER_COMMAND)
async def sport_cmd_start(message: types.Message):
    logger.info("Starting sport command")
    kb = [
        [types.KeyboardButton(text="Download latest activity")],
        [types.KeyboardButton(text="Sync latest activity")],
        [types.KeyboardButton(text="Sync all daily activities")],
        [types.KeyboardButton(text="Get daily activities")],
    ]

    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer("Action ?", reply_markup=keyboard)
    logger.info("Sport command keyboard sent")
