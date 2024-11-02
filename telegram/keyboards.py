from aiogram import types

from telegram.enums import DailyActivitiesDateTypes

__all__ = ["get_activities_dates_keyboard"]


def get_activities_dates_keyboard(callback_data_prefix: str | None = ""):
    kb = [
        [
            types.InlineKeyboardButton(
                text="Yesterday",
                callback_data=f"{callback_data_prefix} {DailyActivitiesDateTypes.yesterday.value}",
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Today",
                callback_data=f"{callback_data_prefix} {DailyActivitiesDateTypes.today.value}",
            )
        ],
    ]

    return types.InlineKeyboardMarkup(inline_keyboard=kb)
