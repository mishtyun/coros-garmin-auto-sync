import logging
from datetime import datetime

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from telegram.calendar.keyboards import generate_calendar
from telegram.utils import local_now
from telegram.handlers.sport.calendar_state import calendar_datepicker_user_data
from telegram.handlers.sport.daily_get_handlers import (
    process_get_callback_button_after_datepicker,
)
from telegram.handlers.sport.daily_sync_handlers import (
    process_sync_callback_button_after_datepicker,
)
from telegram.states.date_picker import CalendarDatePicker
from users.context import UserContext

logger = logging.getLogger(__name__)

__all__ = ["calendar_router"]

calendar_router = Router()


@calendar_router.message(StateFilter(CalendarDatePicker.choosing_date))
@calendar_router.callback_query(F.data.startswith("day_"))
async def process_day_selection(
    callback: types.CallbackQuery, state: FSMContext, user_ctx: UserContext
):
    _, year, month, day = callback.data.split("_")
    formatted_date = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    data = await state.get_data()
    action = data.get("action", "get")
    await state.clear()

    if action == "sync":
        await process_sync_callback_button_after_datepicker(
            callback, user_ctx, formatted_date, formatted_date
        )
    else:
        await process_get_callback_button_after_datepicker(
            callback, user_ctx, formatted_date, formatted_date
        )


@calendar_router.message(StateFilter(CalendarDatePicker.choosing_date))
@calendar_router.callback_query(F.data.startswith("prev_month_"))
async def process_prev_month(callback: types.CallbackQuery):
    """Обработчик перехода на предыдущий месяц"""
    try:
        _, year, month = callback.data.split("_")[1:]
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


@calendar_router.message(StateFilter(CalendarDatePicker.choosing_date))
@calendar_router.callback_query(F.data.startswith("next_month_"))
async def process_next_month(callback: types.CallbackQuery):
    """Обработчик перехода на следующий месяц"""
    try:
        _, year, month = callback.data.split("_")[1:]
        year, month = int(year), int(month)

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


@calendar_router.message(StateFilter(CalendarDatePicker.choosing_date))
@calendar_router.callback_query(F.data == "current_month")
async def process_current_month(callback: types.CallbackQuery):
    """Обработчик кнопки 'Текущий месяц'"""
    try:
        now = local_now()
        user_id = callback.from_user.id

        if (
            user_id in calendar_datepicker_user_data
            and calendar_datepicker_user_data[user_id]["year"] == now.year
            and calendar_datepicker_user_data[user_id]["month"] == now.month
        ):
            return

        calendar_datepicker_user_data[user_id] = {"year": now.year, "month": now.month}
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
