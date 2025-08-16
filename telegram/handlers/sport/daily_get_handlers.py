import logging
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from telegram.calendar.keyboards import generate_calendar
from telegram.enums import DailyActivitiesDateTypes
from telegram.handlers.sport.core import garmin_api
from telegram.keyboards import SportActionButtons, get_activities_dates_inline_keyboard
from telegram.states.date_picker import CalendarDatePicker
from telegram.utils import get_activities_reply

logger = logging.getLogger(__name__)

__all__ = ["daily_router"]

daily_router = Router()


calendar_datepicker_user_data = {}


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
    await state.set_state(CalendarDatePicker.choosing_date)


@daily_router.callback_query(F.data.startswith("get"))
async def process_get_callback_button(callback_query: types.CallbackQuery):
    logger.info(f"Processing get callback: {callback_query.data}")
    choice = callback_query.data

    date_format = "%Y-%m-%d"
    start_date = end_date = None

    if choice.endswith(DailyActivitiesDateTypes.yesterday.value):
        start_date = end_date = (datetime.now() - timedelta(1)).strftime(date_format)
    elif choice.endswith(DailyActivitiesDateTypes.today.value):
        start_date = end_date = datetime.now().strftime(date_format)

    await process_get_callback_button_after_datepicker(
        callback_query, start_date, end_date
    )


async def process_get_callback_button_after_datepicker(
    callback_query: types.CallbackQuery, start_date, end_date
):
    if not start_date or not end_date:
        logger.warning("Invalid dates for get")
        return await callback_query.message.answer("Invalid dates")

    logger.info(f"Getting activities for date range: {start_date} to {end_date}")
    activities = garmin_api.get_activities_by_date(
        start_date=start_date, end_date=end_date
    )
    await get_activities_reply(callback_query, activities, start_date, end_date)

    logger.info(
        f"Activities retrieved and message sent for date range: {start_date} to {end_date}"
    )


@daily_router.message(StateFilter(CalendarDatePicker.choosing_date))
@daily_router.callback_query(F.data.startswith("day_"))
async def process_day_selection(callback: types.CallbackQuery, state: FSMContext):
    _, year, month, day = callback.data.split("_")
    formatted_date = f"{year}-{month}-{day}"

    await process_get_callback_button_after_datepicker(
        callback, formatted_date, formatted_date
    )
    await state.clear()


@daily_router.message(StateFilter(CalendarDatePicker.choosing_date))
@daily_router.callback_query(F.data.startswith("prev_month_"))
async def process_prev_month(callback: types.CallbackQuery):
    """Обработчик перехода на предыдущий месяц"""
    try:
        _, year, month = callback.data.split("_")[
            1:
        ]  # Пропускаем первый элемент "prev"
        year, month = int(year), int(month)

        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1

        calendar_datepicker_user_data[callback.from_user.id] = {
            "year": year,
            "month": month,
        }
        markup = await generate_calendar(year, month)
        await callback.message.edit_reply_markup(reply_markup=markup)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_prev_month: {e}")
        await callback.answer(
            "Произошла ошибка при переходе на предыдущий месяц", show_alert=True
        )


@daily_router.message(StateFilter(CalendarDatePicker.choosing_date))
@daily_router.callback_query(F.data.startswith("next_month_"))
async def process_next_month(callback: types.CallbackQuery):
    """Обработчик перехода на следующий месяц"""
    try:
        # Парсим данные из callback (формат: "next_month_2023_11")
        _, year, month = callback.data.split("_")[
            1:
        ]  # Пропускаем первый элемент "next"
        year, month = int(year), int(month)

        # Вычисляем следующий месяц
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1

        calendar_datepicker_user_data[callback.from_user.id] = {
            "year": year,
            "month": month,
        }
        markup = await generate_calendar(year, month)

        await callback.message.edit_reply_markup(reply_markup=markup)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_next_month: {e}")
        await callback.answer(
            "Произошла ошибка при переходе на следующий месяц", show_alert=True
        )


@daily_router.message(StateFilter(CalendarDatePicker.choosing_date))
@daily_router.callback_query(F.data == "current_month")
async def process_current_month(callback: types.CallbackQuery):
    """Обработчик кнопки 'Текущий месяц'"""
    try:
        now = datetime.now()
        user_id = callback.from_user.id

        if (
            user_id in calendar_datepicker_user_data
            and calendar_datepicker_user_data[user_id]["year"] == now.year
            and calendar_datepicker_user_data[user_id]["month"] == now.month
        ):
            return

        [user_id] = {"year": now.year, "month": now.month}
        markup = await generate_calendar(now.year, now.month)

        try:
            await callback.message.edit_reply_markup(reply_markup=markup)
            await callback.answer("Текущий месяц")
        except Exception as e:
            logging.error(f"Error editing message: {e}")
            await callback.answer("Ошибка обновления календаря", show_alert=True)
    except Exception as e:
        logging.error(f"Error in process_today: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
