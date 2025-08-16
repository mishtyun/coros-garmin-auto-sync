import logging
from datetime import datetime, timedelta

from aiogram import F, Router, types

from telegram.enums import DailyActivitiesDateTypes
from telegram.handlers.sport.core import garmin_api
from telegram.keyboards import SportActionButtons, get_activities_dates_inline_keyboard
from telegram.utils import get_activities_reply

logger = logging.getLogger(__name__)

__all__ = ["daily_router"]

daily_router = Router()


@daily_router.message(F.text == SportActionButtons.SYNC_DAILY)
async def sync_all_daily_activities_button_handler(message: types.Message):
    logger.info("Preparing to sync all daily activities")
    keyboard = get_activities_dates_inline_keyboard(callback_data_prefix="sync")
    await message.reply("When", reply_markup=keyboard)
    logger.info("Sent date selection keyboard for syncing all daily activities")


@daily_router.callback_query(F.data.startswith("sync"))
async def process_sync_callback_button(callback_query: types.CallbackQuery):
    logger.info(f"Processing sync callback: {callback_query.data}")
    from telegram.utils import sync_all_activity_by_dates_handler

    choice = callback_query.data

    date_format, coros_date_format = "%Y-%m-%d", "%Y%m%d"
    start_date = end_date = None

    if choice.endswith(DailyActivitiesDateTypes.yesterday.value):
        start_date = end_date = datetime.now() - timedelta(1)
    elif choice.endswith(DailyActivitiesDateTypes.today.value):
        start_date = end_date = datetime.now()

    if not start_date or not end_date:
        logger.warning("Invalid dates for sync")
        return await callback_query.message.answer("Invalid dates")

    logger.info(f"Syncing activities for date range: {start_date} to {end_date}")
    await sync_all_activity_by_dates_handler(
        garmin_api,
        start_date.strftime(coros_date_format),
        end_date.strftime(coros_date_format),
    )

    activities = garmin_api.get_activities_by_date(
        start_date=start_date.strftime(date_format),
        end_date=end_date.strftime(date_format),
    )
    await get_activities_reply(callback_query, activities, start_date, end_date)

    logger.info(
        f"Sync completed and message sent for date range: {start_date} to {end_date}"
    )
