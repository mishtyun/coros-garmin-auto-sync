import calendar

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def generate_calendar(year, month):
    """Генерация календаря для указанного года и месяца"""
    markup = InlineKeyboardBuilder()

    # Заголовок с месяцем и годом
    month_name = calendar.month_name[month]
    header = f"{month_name} {year}"

    # Кнопки для навигации
    markup.row(
        InlineKeyboardButton(text="<", callback_data=f"prev_month_{year}_{month}"),
        InlineKeyboardButton(text=header, callback_data="ignore"),
        InlineKeyboardButton(text=">", callback_data=f"next_month_{year}_{month}"),
    )

    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    buttons = [
        InlineKeyboardButton(text=day, callback_data="ignore") for day in week_days
    ]
    markup.row(*buttons)

    # Генерация дней месяца
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        buttons = []
        for day in week:
            if day == 0:
                buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                buttons.append(
                    InlineKeyboardButton(
                        text=str(day), callback_data=f"day_{year}_{month}_{day}"
                    )
                )
        markup.row(*buttons)

    # Кнопка "Текущий месяц"
    markup.row(InlineKeyboardButton(text="Текущий месяц", callback_data="current_month"))

    return markup.as_markup()
