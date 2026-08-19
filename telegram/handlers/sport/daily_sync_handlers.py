import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from telegram.calendar.keyboards import generate_calendar
from telegram.enums import DailyActivitiesDateTypes
from telegram.handlers.sport.calendar_state import calendar_datepicker_user_data
from telegram.keyboards import (
    SportActionCallbacks,
    get_activities_dates_inline_keyboard,
)
from telegram.states.date_picker import CalendarDatePicker
from telegram.utils import get_activities_reply, local_now
from users.context import UserContext

logger = logging.getLogger(__name__)

__all__ = ["daily_router", "process_sync_callback_button_after_datepicker"]

daily_router = Router()

DATE_FORMAT = "%Y-%m-%d"


@daily_router.callback_query(F.data == SportActionCallbacks.SYNC_TODAY)
async def sync_today_button_handler(
    callback_query: types.CallbackQuery, user_ctx: UserContext
):
    logger.info("Syncing today's activities")
    await callback_query.answer("Syncing today...")
    today = local_now().strftime(DATE_FORMAT)
    await process_sync_callback_button_after_datepicker(
        callback_query, user_ctx, today, today
    )


@daily_router.callback_query(F.data == SportActionCallbacks.SYNC_DAILY)
async def sync_all_daily_activities_button_handler(
    callback_query: types.CallbackQuery,
):
    logger.info("Preparing to sync all daily activities")
    await callback_query.answer()
    # Today has its own quick button, so the date choice offers yesterday/calendar
    keyboard = get_activities_dates_inline_keyboard(
        callback_data_prefix="sync", include_today=False
    )
    await callback_query.message.answer("When", reply_markup=keyboard)
    logger.info("Sent date selection keyboard for syncing all daily activities")


@daily_router.callback_query(F.data.startswith("sync__date_from_calendar"))
async def process_sync__date_from_calendar(
    callback_query: types.CallbackQuery, state: FSMContext
):
    logger.info(f"Processing sync callback: {callback_query.data}")

    now = local_now()
    calendar_datepicker_user_data[callback_query.from_user.id] = {
        "year": now.year,
        "month": now.month,
    }

    markup = await generate_calendar(now.year, now.month)
    await callback_query.message.answer("Выберите дату:", reply_markup=markup)
    await state.update_data(action="sync")
    await state.set_state(CalendarDatePicker.choosing_date)


@daily_router.callback_query(F.data.startswith("sync"))
async def process_sync_callback_button(
    callback_query: types.CallbackQuery, user_ctx: UserContext
):
    logger.info(f"Processing sync callback: {callback_query.data}")

    choice = callback_query.data
    start_date = end_date = None

    if choice.endswith(DailyActivitiesDateTypes.yesterday.value):
        start_date = end_date = (local_now() - timedelta(1)).strftime(DATE_FORMAT)
    elif choice.endswith(DailyActivitiesDateTypes.today.value):
        start_date = end_date = local_now().strftime(DATE_FORMAT)

    await process_sync_callback_button_after_datepicker(
        callback_query, user_ctx, start_date, end_date
    )


async def process_sync_callback_button_after_datepicker(
    callback_query: types.CallbackQuery,
    user_ctx: UserContext,
    start_date: str | None,
    end_date: str | None,
):
    if not start_date or not end_date:
        logger.warning("Invalid dates for sync")
        return await callback_query.message.answer("Invalid dates")

    logger.info(f"Syncing activities for date range: {start_date} to {end_date}")
    from telegram.utils import sync_all_activity_by_dates_handler

    garmin_api = await user_ctx.get_garmin()
    await sync_all_activity_by_dates_handler(
        garmin_api,
        user_ctx.coros_config,
        start_date.replace("-", ""),
        end_date.replace("-", ""),
    )

    activities = await asyncio.to_thread(
        garmin_api.get_activities_by_date,
        start_date=start_date,
        end_date=end_date,
    )
    await get_activities_reply(callback_query, activities, start_date, end_date)

    logger.info(
        f"Sync completed and message sent for date range: {start_date} to {end_date}"
    )
