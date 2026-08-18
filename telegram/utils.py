import asyncio
import html
import logging
from asyncio import sleep
from typing import IO

from aiogram import methods, types
from pydantic import TypeAdapter

from coros.configuration import CorosConfiguration
from coros.models import DateActivityFilter
from coros.services import AuthService
from coros.services.activity import ActivityService
from garmin.client import Garmin, GarthHTTPError
from telegram.schemas.activity import GarminActivitiesSchema

logger = logging.getLogger(__name__)


__all__ = [
    "get_activity_url",
    "get_activity_emoji",
    "format_distance",
    "format_duration",
    "build_activity_title",
    "upload_and_get_url",
    "get_activities_message_text",
    "get_activities_reply",
    "sync_all_activity_by_dates_handler",
]

ACTIVITY_TYPE_EMOJI = {
    "running": "🏃",
    "trail_running": "🏃",
    "treadmill_running": "🏃",
    "track_running": "🏃",
    "cycling": "🚴",
    "road_biking": "🚴",
    "indoor_cycling": "🚴",
    "virtual_ride": "🚴",
    "mountain_biking": "🚵",
    "gravel_cycling": "🚵",
    "swimming": "🏊",
    "lap_swimming": "🏊",
    "open_water_swimming": "🏊",
    "strength_training": "🏋️",
    "indoor_cardio": "🏋️",
    "walking": "🚶",
    "hiking": "🥾",
}
DEFAULT_ACTIVITY_EMOJI = "🏅"

ACTIVITY_TYPE_LABEL = {
    "running": "Run",
    "trail_running": "Trail Run",
    "treadmill_running": "Treadmill Run",
    "track_running": "Track Run",
    "cycling": "Ride",
    "road_biking": "Ride",
    "indoor_cycling": "Indoor Ride",
    "virtual_ride": "Virtual Ride",
    "mountain_biking": "MTB Ride",
    "gravel_cycling": "Gravel Ride",
    "swimming": "Swim",
    "lap_swimming": "Swim",
    "open_water_swimming": "Open Water Swim",
    "strength_training": "Strength",
    "walking": "Walk",
    "hiking": "Hike",
}


def get_activity_url(activity_id: str):
    return f"https://connect.garmin.com/modern/activity/{activity_id}"


def get_activity_emoji(type_key: str) -> str:
    return ACTIVITY_TYPE_EMOJI.get(type_key, DEFAULT_ACTIVITY_EMOJI)


def get_activity_type_label(type_key: str) -> str:
    if label := ACTIVITY_TYPE_LABEL.get(type_key):
        return label
    return type_key.replace("_", " ").title() if type_key else "Workout"


def format_distance(meters: float | None) -> str | None:
    if not meters:
        return None
    return f"{meters / 1000:.1f} km"


def format_duration(seconds: float | None) -> str | None:
    if not seconds:
        return None
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def get_part_of_day(start_time_local: str) -> str:
    # start_time_local format: "2026-08-08 07:30:00"
    try:
        hour = int(start_time_local[11:13])
    except (ValueError, IndexError):
        return ""

    if hour < 5:
        return "Night"
    if hour < 12:
        return "Morning"
    if hour < 17:
        return "Afternoon"
    if hour < 22:
        return "Evening"
    return "Night"


def build_activity_title(activity: dict) -> str:
    """Build a pretty Garmin activity name like '🏃 Morning Run · 10.2 km'."""
    type_key = (activity.get("activityType") or {}).get("typeKey", "")
    emoji = get_activity_emoji(type_key)
    label = get_activity_type_label(type_key)
    part_of_day = get_part_of_day(activity.get("startTimeLocal") or "")

    title = f"{emoji} {part_of_day} {label}".replace("  ", " ").strip()

    if distance := format_distance(activity.get("distance")):
        title += f" · {distance}"

    return title


async def upload_and_get_url(
    garmin_api: Garmin, file_name: str, file: IO[bytes]
) -> tuple[bool, str] | tuple[bool, None]:
    try:
        await asyncio.to_thread(garmin_api.upload_activity_from_binary, file_name, file)
        uploaded = True
        await sleep(3)
    except GarthHTTPError as e:
        error_json: dict = e.error.response.json()
        error_messages = (
            error_json.get("detailedImportResult").get("failures")[0].get("messages")
        )

        duplicate_message = {"code": 202, "content": "Duplicate Activity."}

        if duplicate_message not in error_messages:
            raise Exception from e

        uploaded = False
        logger.info("ActivityShortSchema already exists. Skipping upload.")

    except Exception as e:
        logger.error(e)
        return False, None

    latest_activity = await asyncio.to_thread(garmin_api.get_last_activity)
    activity_id = latest_activity.get("activityId")

    await asyncio.to_thread(
        garmin_api.change_activity_visibility, activity_id, "public"
    )
    return uploaded, get_activity_url(activity_id)


async def sync_all_activity_by_dates_handler(
    garmin_api: Garmin,
    coros_config: CorosConfiguration,
    start_date: str,
    end_date: str,
) -> list[str]:
    """
    Sync (download from Coros and upload into Garmin) available activities between specific dates
    :param garmin_api: Garmin-Api instance
    :param coros_config: per-user Coros configuration
    :param start_date: String in the format YYYYMMDD
    :param end_date: String in the format YYYYMMDD
    :return: list of activity links
    """

    await asyncio.to_thread(AuthService(coros_config).get_or_set_access_token)

    files = await asyncio.to_thread(
        ActivityService(coros_config).get_daily_activities_bytes,
        DateActivityFilter(start_date=start_date, end_date=end_date),
    )

    activity_links = []

    for file_name, file_content in files:
        _, garmin_activity_link = await upload_and_get_url(
            garmin_api, file_name=file_name, file=file_content
        )
        if not garmin_activity_link:
            activity_links.append("One of the activity was synced already :)")
            continue
        activity_links.append(garmin_activity_link)

    return activity_links


def get_activities_message_text(activities: GarminActivitiesSchema) -> str:
    lines = []
    for activity in activities:
        emoji = get_activity_emoji(activity.activity_type.type_key)
        name = html.escape(activity.activity_name)
        activity_url = get_activity_url(activity.activity_id)

        details = " · ".join(
            part
            for part in (
                format_distance(activity.distance),
                format_duration(activity.duration),
            )
            if part
        )

        line = f'{emoji} <a href="{activity_url}">{name}</a>'
        if details:
            line += f" — {details}"
        lines.append(line)

    return "\n".join(lines)


def get_activities_reply(
    callback_query: types.CallbackQuery,
    activities: list[dict],
    start_date: str,
    end_date: str,
) -> methods.SendMessage:
    activities = TypeAdapter(GarminActivitiesSchema).validate_python(activities)
    message_text = get_activities_message_text(activities)

    if not message_text:
        return callback_query.answer("No activities :(")

    start, end = str(start_date)[:10], str(end_date)[:10]
    period = start if start == end else f"{start} → {end}"

    return callback_query.message.answer(
        f"📊 <b>Activities · {period}</b>\n\n{message_text}",
        parse_mode="HTML",
        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
    )
