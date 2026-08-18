from aiogram import types

from telegram.enums import DailyActivitiesDateTypes

__all__ = [
    "SportActionButtons",
    "SportActionCallbacks",
    "get_sport_action_inline_keyboard",
    "get_activities_dates_inline_keyboard",
]


class SportActionButtons:
    DOWNLOAD_LATEST = "⬇️ Download latest"
    SYNC_LATEST = "🔄 Sync latest"
    SYNC_DAILY = "📅 Sync daily"
    GET_DAILY = "📥 Get daily"


class SportActionCallbacks:
    DOWNLOAD_LATEST = "sport:download_latest"
    SYNC_LATEST = "sport:sync_latest"
    SYNC_DAILY = "sport:sync_daily"
    GET_DAILY = "sport:get_daily"


def get_sport_action_inline_keyboard() -> types.InlineKeyboardMarkup:
    kb = [
        [
            types.InlineKeyboardButton(
                text=SportActionButtons.DOWNLOAD_LATEST,
                callback_data=SportActionCallbacks.DOWNLOAD_LATEST,
            ),
            types.InlineKeyboardButton(
                text=SportActionButtons.SYNC_LATEST,
                callback_data=SportActionCallbacks.SYNC_LATEST,
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=SportActionButtons.SYNC_DAILY,
                callback_data=SportActionCallbacks.SYNC_DAILY,
            ),
            types.InlineKeyboardButton(
                text=SportActionButtons.GET_DAILY,
                callback_data=SportActionCallbacks.GET_DAILY,
            ),
        ],
    ]

    return types.InlineKeyboardMarkup(inline_keyboard=kb)


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
