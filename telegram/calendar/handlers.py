import logging
from datetime import datetime

from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart

from telegram.calendar.keyboards import generate_calendar

router = Router()


# Храним текущий год и месяц для каждого пользователя
user_data = {}


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /hello"""
    now = datetime.now()
    user_data[message.from_user.id] = {"year": now.year, "month": now.month}

    markup = await generate_calendar(now.year, now.month)
    await message.answer("Выберите дату:", reply_markup=markup)


@router.callback_query(F.data.startswith("day_"))
async def process_day_selection(callback: types.CallbackQuery):
    """Обработчик выбора дня"""
    _, year, month, day = callback.data.split("_")
    await callback.answer(f"Вы выбрали {day}.{month}.{year}")


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

        user_data[callback.from_user.id] = {"year": year, "month": month}
        markup = await generate_calendar(year, month)
        await callback.message.edit_reply_markup(reply_markup=markup)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_prev_month: {e}")
        await callback.answer(
            "Произошла ошибка при переходе на предыдущий месяц", show_alert=True
        )


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

        # Обновляем данные пользователя
        user_data[callback.from_user.id] = {"year": year, "month": month}

        # Генерируем новую клавиатуру
        markup = await generate_calendar(year, month)

        # Обновляем сообщение
        await callback.message.edit_reply_markup(reply_markup=markup)
        await callback.answer()
    except Exception as e:
        logging.error(f"Error in process_next_month: {e}")
        await callback.answer(
            "Произошла ошибка при переходе на следующий месяц", show_alert=True
        )


@router.callback_query(F.data == "current_month")
async def process_current_month(callback: types.CallbackQuery):
    """Обработчик кнопки 'Текущий месяц'"""
    try:
        now = datetime.now()
        user_id = callback.from_user.id

        # Проверяем, не пытаемся ли обновить на тот же месяц
        if (
            user_id in user_data
            and user_data[user_id]["year"] == now.year
            and user_data[user_id]["month"] == now.month
        ):
            # await callback.answer("Уже отображается текущий месяц")
            return

        user_data[user_id] = {"year": now.year, "month": now.month}
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
