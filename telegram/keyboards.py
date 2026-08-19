from aiogram import types

from telegram.enums import DailyActivitiesDateTypes

__all__ = [
    "SportActionButtons",
    "SportActionCallbacks",
    "WorkoutPlannerButtons",
    "WorkoutPlannerCallbacks",
    "get_sport_action_inline_keyboard",
    "get_sport_more_inline_keyboard",
    "get_activities_dates_inline_keyboard",
    "get_workout_confirm_inline_keyboard",
]


class SportActionButtons:
    SYNC_TODAY = "🔄 Sync today"
    SYNC_DAILY = "📅 Sync daily"
    GET_DAILY = "📥 Get daily"
    MORE = "⚙️ More"
    DOWNLOAD_LATEST = "⬇️ Download latest"
    SYNC_LATEST = "🔃 Sync latest"
    BACK = "⬅️ Back"


class WorkoutPlannerButtons:
    CONFIRM = "✅ Schedule it"
    CANCEL = "❌ Cancel"


class WorkoutPlannerCallbacks:
    CONFIRM = "workout:confirm"
    CANCEL = "workout:cancel"


class SportActionCallbacks:
    SYNC_TODAY = "sport:sync_today"
    SYNC_DAILY = "sport:sync_daily"
    GET_DAILY = "sport:get_daily"
    MORE = "sport:more"
    MENU = "sport:menu"
    DOWNLOAD_LATEST = "sport:download_latest"
    SYNC_LATEST = "sport:sync_latest"


def get_sport_action_inline_keyboard() -> types.InlineKeyboardMarkup:
    kb = [
        [
            types.InlineKeyboardButton(
                text=SportActionButtons.SYNC_TODAY,
                callback_data=SportActionCallbacks.SYNC_TODAY,
            ),
            types.InlineKeyboardButton(
                text=SportActionButtons.GET_DAILY,
                callback_data=SportActionCallbacks.GET_DAILY,
            ),
        ],
        [
            types.InlineKeyboardButton(
                text=SportActionButtons.SYNC_DAILY,
                callback_data=SportActionCallbacks.SYNC_DAILY,
            ),
            types.InlineKeyboardButton(
                text=SportActionButtons.MORE,
                callback_data=SportActionCallbacks.MORE,
            ),
        ],
    ]

    return types.InlineKeyboardMarkup(inline_keyboard=kb)


def get_sport_more_inline_keyboard() -> types.InlineKeyboardMarkup:
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
                text=SportActionButtons.BACK,
                callback_data=SportActionCallbacks.MENU,
            ),
        ],
    ]

    return types.InlineKeyboardMarkup(inline_keyboard=kb)


def get_workout_confirm_inline_keyboard() -> types.InlineKeyboardMarkup:
    kb = [
        [
            types.InlineKeyboardButton(
                text=WorkoutPlannerButtons.CONFIRM,
                callback_data=WorkoutPlannerCallbacks.CONFIRM,
            ),
            types.InlineKeyboardButton(
                text=WorkoutPlannerButtons.CANCEL,
                callback_data=WorkoutPlannerCallbacks.CANCEL,
            ),
        ],
    ]

    return types.InlineKeyboardMarkup(inline_keyboard=kb)


def get_activities_dates_inline_keyboard(
    callback_data_prefix: str | None = "",
    include_today: bool = True,
) -> types.InlineKeyboardMarkup:
    kb = [
        [
            types.InlineKeyboardButton(
                text="Yesterday",
                callback_data=f"{callback_data_prefix} {DailyActivitiesDateTypes.yesterday.value}",
            )
        ],
    ]

    if include_today:
        kb.append(
            [
                types.InlineKeyboardButton(
                    text="Today",
                    callback_data=f"{callback_data_prefix} {DailyActivitiesDateTypes.today.value}",
                )
            ]
        )

    kb.append(
        [
            types.InlineKeyboardButton(
                text="Calendar",
                callback_data=f"{callback_data_prefix}__date_from_calendar",
            )
        ]
    )

    return types.InlineKeyboardMarkup(inline_keyboard=kb)
