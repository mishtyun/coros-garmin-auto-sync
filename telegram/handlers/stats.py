import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router, types
from aiogram.filters import Command
from pydantic import TypeAdapter

from telegram.schemas.activity import GarminActivitiesSchema
from telegram.utils import (
    format_distance,
    format_duration,
    get_activity_emoji,
    get_activity_type_label,
)
from users.context import UserContext
from users.models import UserProfile
from users.repository import get_user_redis_repository

logger = logging.getLogger(__name__)

__all__ = ["stats_router", "build_stats_text"]

stats_router = Router()

DATE_FORMAT = "%Y-%m-%d"

STATS_PERIODS = {
    "week": "This week",
    "last_week": "Last week",
    "month": "This month",
}


def get_period_dates(period: str) -> tuple[str, str]:
    today = datetime.now(timezone.utc).date()

    if period == "last_week":
        monday = today - timedelta(days=today.weekday() + 7)
        return str(monday), str(monday + timedelta(days=6))
    if period == "month":
        return str(today.replace(day=1)), str(today)

    # this week
    return str(today - timedelta(days=today.weekday())), str(today)


async def build_stats_text(
    profile: UserProfile, start_date: str, end_date: str, label: str
) -> str | None:
    """Aggregate Garmin activities for the period; None when there are none."""
    user_ctx = UserContext(tg_id=profile.tg_id, profile=profile)
    garmin_api = await user_ctx.get_garmin()

    raw_activities = await asyncio.to_thread(
        garmin_api.get_activities_by_date, start_date=start_date, end_date=end_date
    )
    activities = TypeAdapter(GarminActivitiesSchema).validate_python(raw_activities)
    if not activities:
        return None

    total_distance = sum(activity.distance or 0 for activity in activities)
    total_duration = sum(activity.duration or 0 for activity in activities)

    totals = " · ".join(
        part
        for part in (
            f"{len(activities)} workouts",
            format_distance(total_distance),
            format_duration(total_duration),
        )
        if part
    )

    by_type: dict[str, dict] = {}
    for activity in activities:
        type_key = activity.activity_type.type_key
        stats = by_type.setdefault(
            type_key, {"count": 0, "distance": 0.0, "duration": 0.0}
        )
        stats["count"] += 1
        stats["distance"] += activity.distance or 0
        stats["duration"] += activity.duration or 0

    type_lines = []
    for type_key, stats in sorted(
        by_type.items(), key=lambda item: item[1]["duration"], reverse=True
    ):
        line = (
            f"{get_activity_emoji(type_key)} "
            f"{get_activity_type_label(type_key)} — {stats['count']}"
        )
        if distance := format_distance(stats["distance"]):
            line += f" · {distance}"
        type_lines.append(line)

    period = start_date if start_date == end_date else f"{start_date} → {end_date}"
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

    return text or f"No workouts in {label.lower()} yet 💤"


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
