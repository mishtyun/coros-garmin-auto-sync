import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.filters import Command

from coros.configuration import CorosConfiguration
from coros.models import DateActivityFilter
from coros.services import ActivityService, AuthService
from coros.services.auth import CorosAuthError
from telegram.utils import (
    format_distance,
    format_duration,
    get_coros_sport_emoji_label,
    local_now,
)
from users.models import UserProfile
from users.repository import get_user_redis_repository

logger = logging.getLogger(__name__)

__all__ = ["stats_router", "build_stats_data", "build_stats_text"]

stats_router = Router()

DATE_FORMAT = "%Y-%m-%d"

STATS_PERIODS = {
    "week": "This week",
    "last_week": "Last week",
    "month": "This month",
}


def get_period_dates(period: str) -> tuple[str, str]:
    today = local_now().date()

    if period == "last_week":
        monday = today - timedelta(days=today.weekday() + 7)
        return str(monday), str(monday + timedelta(days=6))
    if period == "month":
        return str(today.replace(day=1)), str(today)

    # this week
    return str(today - timedelta(days=today.weekday())), str(today)


def format_period(start_date: str, end_date: str) -> str:
    start = datetime.fromisoformat(start_date).strftime("%a %d.%m")
    end = datetime.fromisoformat(end_date).strftime("%a %d.%m")
    return start if start == end else f"{start} → {end}"


async def build_stats_data(
    profile: UserProfile, start_date: str, end_date: str
) -> dict | None:
    """Aggregate Coros activities for the period; None when there are none.

    Coros (not Garmin) is the source of truth here: stats include workouts
    that haven't been synced yet and work even if the Garmin session is dead.
    """
    coros_config = CorosConfiguration(
        email=profile.coros_email, password_md5=profile.coros_password_md5
    )

    access_token = await asyncio.to_thread(
        AuthService(coros_config).get_or_set_access_token
    )
    if not access_token:
        raise CorosAuthError(f"Coros auth failed for {profile.coros_email}")

    date_filters = DateActivityFilter(
        start_date=start_date.replace("-", ""), end_date=end_date.replace("-", "")
    )
    activities = await asyncio.to_thread(
        ActivityService(coros_config).get_activities, date_filters
    )
    if not activities:
        return None

    # group by human label so e.g. outdoor and helmet rides merge into one "Ride" line
    by_type: dict[tuple[str, str], dict] = {}
    for activity in activities:
        group = get_coros_sport_emoji_label(activity.sport_type)
        stats = by_type.setdefault(
            group, {"count": 0, "distance": 0.0, "duration": 0.0}
        )
        stats["count"] += 1
        stats["distance"] += activity.distance or 0
        stats["duration"] += activity.duration or 0

    return {
        "totals": {
            "count": len(activities),
            "distance_m": sum(activity.distance or 0 for activity in activities),
            "duration_s": sum(activity.duration or 0 for activity in activities),
        },
        "by_type": [
            {
                "emoji": emoji,
                "label": type_label,
                "count": stats["count"],
                "distance_m": stats["distance"],
                "duration_s": stats["duration"],
            }
            for (emoji, type_label), stats in sorted(
                by_type.items(), key=lambda item: item[1]["duration"], reverse=True
            )
        ],
    }


async def build_stats_text(
    profile: UserProfile, start_date: str, end_date: str, label: str
) -> str | None:
    data = await build_stats_data(profile, start_date, end_date)
    if data is None:
        return None

    totals = " · ".join(
        part
        for part in (
            f"{data['totals']['count']} workouts",
            format_distance(data["totals"]["distance_m"]),
            format_duration(data["totals"]["duration_s"]),
        )
        if part
    )

    type_lines = []
    for group in data["by_type"]:
        line = f"{group['emoji']} {group['label']} — {group['count']}"
        details = " · ".join(
            part
            for part in (
                format_distance(group["distance_m"]),
                format_duration(group["duration_s"]),
            )
            if part
        )
        if details:
            line += f" · {details}"
        type_lines.append(line)

    period = format_period(start_date, end_date)
    return f"📊 <b>{label}</b> · {period}\n{totals}\n\n" + "\n".join(type_lines)


def get_stats_keyboard(profile: UserProfile) -> types.InlineKeyboardMarkup:
    digest_text = "📬 Digest: ON" if profile.digest else "📭 Digest: OFF"
    kb = [
        [
            types.InlineKeyboardButton(text="This week", callback_data="stats:week"),
            types.InlineKeyboardButton(
                text="Last week", callback_data="stats:last_week"
            ),
            types.InlineKeyboardButton(text="This month", callback_data="stats:month"),
        ],
        [
            types.InlineKeyboardButton(
                text=digest_text, callback_data="stats:digest_toggle"
            ),
        ],
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)


async def get_stats_message_text(profile: UserProfile, period: str) -> str:
    label = STATS_PERIODS.get(period, STATS_PERIODS["week"])
    start_date, end_date = get_period_dates(period)

    try:
        text = await build_stats_text(profile, start_date, end_date, label)
    except Exception as e:
        logger.error(f"Stats failed for tg_id={profile.tg_id}: {e}", exc_info=True)
        return "Couldn't load stats — try again later."

    period = format_period(start_date, end_date)
    return text or f"No workouts in {label.lower()} ({period}) yet 💤"


@stats_router.message(Command("stats"))
async def stats_cmd(message: types.Message):
    profile = get_user_redis_repository().get_profile(message.from_user.id)
    if not profile:
        await message.answer("You're not registered yet — send /register")
        return

    text = await get_stats_message_text(profile, "week")
    await message.answer(
        text, parse_mode="HTML", reply_markup=get_stats_keyboard(profile)
    )


@stats_router.callback_query(F.data == "stats:digest_toggle")
async def stats_digest_toggle_callback(callback_query: types.CallbackQuery):
    repository = get_user_redis_repository()
    profile = repository.get_profile(callback_query.from_user.id)
    if not profile:
        await callback_query.answer("You're not registered yet — send /register")
        return

    profile.digest = not profile.digest
    repository.save_profile(profile)

    try:
        await callback_query.message.edit_reply_markup(
            reply_markup=get_stats_keyboard(profile)
        )
    except Exception:
        pass

    await callback_query.answer(
        "Digest on: daily summary every evening, weekly one on Sundays"
        if profile.digest
        else "Digest off"
    )


@stats_router.callback_query(F.data.startswith("stats:"))
async def stats_period_callback(callback_query: types.CallbackQuery):
    profile = get_user_redis_repository().get_profile(callback_query.from_user.id)
    if not profile:
        await callback_query.answer("You're not registered yet — send /register")
        return

    await callback_query.answer()
    period = callback_query.data.split(":", 1)[1]
    text = await get_stats_message_text(profile, period)

    try:
        await callback_query.message.edit_text(
            text, parse_mode="HTML", reply_markup=get_stats_keyboard(profile)
        )
    except Exception:
        # same period pressed twice -> "message is not modified"
        pass
