import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from telegram.calendar.keyboards import generate_calendar
from telegram.enums import DailyActivitiesDateTypes
from telegram.handlers.sport.calendar_state import calendar_datepicker_user_data
from telegram.keyboards import SportActionButtons, get_activities_dates_inline_keyboard
from telegram.states.date_picker import CalendarDatePicker
from telegram.utils import get_activities_reply
from users.context import UserContext

logger = logging.getLogger(__name__)

__all__ = ["daily_router", "process_get_callback_button_after_datepicker"]

daily_router = Router()

DATE_FORMAT = "%Y-%m-%d"


@daily_router.message(F.text == SportActionButtons.GET_DAILY)
async def get_all_daily_activities_button_handler(message: types.Message):
    logger.info("Preparing to get all daily activities")
    keyboard = get_activities_dates_inline_keyboard(callback_data_prefix="get")
    await message.reply("When", reply_markup=keyboard)
    logger.info("Sent date selection keyboard for getting all daily activities")


@daily_router.callback_query(F.data.startswith("get__date_from_calendar"))
async def process_get__date_from_calendar(
    callback_query: types.CallbackQuery, state: FSMContext
):
    logger.info(f"Processing get callback: {callback_query.data}")

    now = datetime.now()
    calendar_datepicker_user_data[callback_query.from_user.id] = {
        "year": now.year,
        "month": now.month,
    }

    markup = await generate_calendar(now.year, now.month)
    await callback_query.message.answer("Выберите дату:", reply_markup=markup)
    await state.update_data(action="get")
    await state.set_state(CalendarDatePicker.choosing_date)


@daily_router.callback_query(F.data.startswith("get"))
async def process_get_callback_button(
    callback_query: types.CallbackQuery, user_ctx: UserContext
):
    logger.info(f"Processing get callback: {callback_query.data}")
    choice = callback_query.data

    start_date = end_date = None

    if choice.endswith(DailyActivitiesDateTypes.yesterday.value):
        start_date = end_date = (datetime.now() - timedelta(1)).strftime(DATE_FORMAT)
    elif choice.endswith(DailyActivitiesDateTypes.today.value):
        start_date = end_date = datetime.now().strftime(DATE_FORMAT)

    await process_get_callback_button_after_datepicker(
        callback_query, user_ctx, start_date, end_date
    )


async def process_get_callback_button_after_datepicker(
    callback_query: types.CallbackQuery, user_ctx: UserContext, start_date, end_date
):
    if not start_date or not end_date:
        logger.warning("Invalid dates for get")
        return await callback_query.message.answer("Invalid dates")

    logger.info(f"Getting activities for date range: {start_date} to {end_date}")
    garmin_api = await user_ctx.get_garmin()
    activities = await asyncio.to_thread(
        garmin_api.get_activities_by_date, start_date=start_date, end_date=end_date
    )
    await get_activities_reply(callback_query, activities, start_date, end_date)

    logger.info(
        f"Activities retrieved and message sent for date range: {start_date} to {end_date}"
    )
