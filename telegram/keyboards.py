from aiogram import types

from telegram.enums import DailyActivitiesDateTypes

__all__ = [
    "SportActionButtons",
    "get_sport_action_keyboard",
    "get_activities_dates_inline_keyboard",
]


class SportActionButtons:
    DOWNLOAD_LATEST = "⬇️ Download latest"
    SYNC_LATEST = "🔄 Sync latest"
    SYNC_DAILY = "📅 Sync daily"
    GET_DAILY = "📥 Get daily"


def get_sport_action_keyboard() -> types.ReplyKeyboardMarkup:
    kb = [
        [
            types.KeyboardButton(text=SportActionButtons.DOWNLOAD_LATEST),
            types.KeyboardButton(text=SportActionButtons.SYNC_LATEST),
        ],
        [
            types.KeyboardButton(text=SportActionButtons.SYNC_DAILY),
            types.KeyboardButton(text=SportActionButtons.GET_DAILY),
        ],
    ]

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
    )
    return keyboard


def get_activities_dates_inline_keyboard(
    callback_data_prefix: str | None = "",
) -> types.InlineKeyboardMarkup:
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
        [
            types.InlineKeyboardButton(
                text="Calendar",
                callback_data=f"{callback_data_prefix}__date_from_calendar",
            )
        ],
    ]

    return types.InlineKeyboardMarkup(inline_keyboard=kb)
