import logging
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from garmin_connect.app import init_api
from garmin_connect.configuration import garmin_connect_configuration
from garmin_connect.repository import FileOAuthRepository

from coros import coros_configuration
from coros.services import ActivityService, AuthService
from telegram.calendar.keyboards import generate_calendar
from telegram.enums import DailyActivitiesDateTypes
from telegram.keyboards import (
    SportActionButtons,
    get_activities_dates_inline_keyboard,
    get_sport_action_keyboard,
)
from telegram.states.date_picker import CalendarDatePicker
from telegram.utils import get_activities_reply, upload_and_get_url

logger = logging.getLogger(__name__)

__all__ = ["router"]

START_HANDLER_COMMAND = "/sport"

router = Router()
garmin_api = init_api(
    oauth_repo=FileOAuthRepository(garmin_connect_configuration.tokenstore),
    garmin_connect_configuration=garmin_connect_configuration,
)

calendar_datepicker_user_data = {}


@router.message(F.text == SportActionButtons.DOWNLOAD_LATEST)
async def download_latest_activity_button_handler(message: types.Message):
    logger.info("Downloading latest activity")
    try:
        AuthService(coros_configuration).get_or_set_access_token()

        activity_name, activity_content = ActivityService(
            coros_configuration
        ).get_latest_activity_bytes()

        if not activity_name or not activity_content:
            logger.info("Latest activity not found")
            await message.answer("Latest activity not found")
            return

        activity_file = BufferedInputFile(
            filename=activity_name, file=activity_content.read()
        )

        await message.reply_document(document=activity_file, caption="Latest activity")
        logger.info(
            f"Successfully downloaded and sent latest activity: {activity_name}"
        )
    except Exception as e:
        logger.error(
            f"Error while downloading latest activity: {str(e)}", exc_info=True
        )
        await message.answer("Error while downloading")


@router.message(F.text == SportActionButtons.SYNC_LATEST)
async def sync_latest_activity_button_handler(message: types.Message):
    logger.info("Syncing latest activity")
    try:
        AuthService(coros_configuration).get_or_set_access_token()
        activity_name, activity_content = ActivityService(
            coros_configuration
        ).get_latest_activity_bytes()

        is_uploaded, garmin_activity_link = await upload_and_get_url(
            garmin_api, file_name=activity_name, file=activity_content
        )

        message_to_answer = (
            f"Synced successfully!\n{garmin_activity_link}"
            if is_uploaded
            else f"Already synced :)\n{garmin_activity_link}"
        )

        await message.reply(message_to_answer)
        logger.info(f"Successfully synced latest activity: {garmin_activity_link}")
    except Exception as e:
        logger.error(f"Error while syncing latest activity: {str(e)}", exc_info=True)
        await message.answer("Error while syncing")


@router.message(F.text == SportActionButtons.SYNC_DAILY)
async def sync_all_daily_activities_button_handler(message: types.Message):
    logger.info("Preparing to sync all daily activities")
    keyboard = get_activities_dates_inline_keyboard(callback_data_prefix="sync")
    await message.reply("When", reply_markup=keyboard)
    logger.info("Sent date selection keyboard for syncing all daily activities")


@router.message(F.text == SportActionButtons.GET_DAILY)
async def get_all_daily_activities_button_handler(message: types.Message):
    logger.info("Preparing to get all daily activities")
    keyboard = get_activities_dates_inline_keyboard(callback_data_prefix="get")
    await message.reply("When", reply_markup=keyboard)
    logger.info("Sent date selection keyboard for getting all daily activities")


@router.callback_query(F.data.startswith("sync"))
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


@router.callback_query(F.data.startswith("get__date_from_calendar"))
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


@router.callback_query(F.data.startswith("get"))
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


@router.message(F.text == START_HANDLER_COMMAND)
async def sport_cmd_start(message: types.Message):
    logger.info("Starting sport command")
    keyboard = get_sport_action_keyboard()

    await message.answer("🏊‍♂️🏃‍♂️🚴‍♀️ Hey athlete!", reply_markup=keyboard)
    logger.info("Sport command keyboard sent")


@router.message(StateFilter(CalendarDatePicker.choosing_date))
@router.callback_query(F.data.startswith("day_"))
async def process_day_selection(callback: types.CallbackQuery, state: FSMContext):
    _, year, month, day = callback.data.split("_")
    formatted_date = f"{year}-{month}-{day}"

    await process_get_callback_button_after_datepicker(
        callback, formatted_date, formatted_date
    )
    await state.clear()


@router.message(StateFilter(CalendarDatePicker.choosing_date))
@router.callback_query(F.data.startswith("prev_month_"))
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


@router.message(StateFilter(CalendarDatePicker.choosing_date))
@router.callback_query(F.data.startswith("next_month_"))
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


@router.message(StateFilter(CalendarDatePicker.choosing_date))
@router.callback_query(F.data == "current_month")
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


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    """Игнорируем ненужные нажатия"""
    await callback.answer()
