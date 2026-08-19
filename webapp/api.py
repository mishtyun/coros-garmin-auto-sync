import asyncio
import functools
import logging
from datetime import timedelta

from aiohttp import web

from webapp.auth import json_error

logger = logging.getLogger(__name__)

__all__ = ["register_api_routes"]


def api_errors(handler):
    from coros.services.auth import CorosAuthError
    from garmin.client import GarminMFARequiredError, GarminSessionExpiredError

    @functools.wraps(handler)
    async def wrapper(request: web.Request) -> web.StreamResponse:
        try:
            return await handler(request)
        except (GarminSessionExpiredError, GarminMFARequiredError):
            return json_error(
                409,
                "garmin_session_expired",
                "Garmin session expired — re-register in the bot chat (/register).",
            )
        except CorosAuthError:
            return json_error(
                409,
                "coros_auth_failed",
                "Coros login failed — re-register in the bot chat (/register).",
            )
        except Exception as e:
            logger.error(f"API error in {handler.__name__}: {e}", exc_info=True)
            return json_error(
                500, "internal", "Something went wrong — try again later."
            )

    return wrapper


def me_payload(profile) -> dict:
    return {
        "tg_id": profile.tg_id,
        "coros_email": profile.coros_email,
        "garmin_email": profile.garmin_email,
        "autosync": profile.autosync,
        "autosync_quiet": profile.autosync_quiet,
        "digest": profile.digest,
        "created_at": profile.created_at,
    }


@api_errors
async def get_me(request: web.Request) -> web.Response:
    return web.json_response(me_payload(request["user_ctx"].profile))


@api_errors
async def get_stats(request: web.Request) -> web.Response:
    from telegram.handlers.stats import (
        STATS_PERIODS,
        build_stats_data,
        get_period_dates,
    )
    from telegram.utils import format_distance, format_duration

    period = request.query.get("period", "week")
    if period not in STATS_PERIODS:
        return json_error(400, "bad_request", f"Unknown period: {period}")

    start_date, end_date = get_period_dates(period)
    profile = request["user_ctx"].profile

    data = await build_stats_data(profile, start_date, end_date)
    if data is None:
        data = {
            "totals": {"count": 0, "distance_m": 0, "duration_s": 0},
            "by_type": [],
        }

    data["totals"]["distance_text"] = format_distance(data["totals"]["distance_m"])
    data["totals"]["duration_text"] = format_duration(data["totals"]["duration_s"])
    for group in data["by_type"]:
        group["distance_text"] = format_distance(group["distance_m"])
        group["duration_text"] = format_duration(group["duration_s"])

    return web.json_response(
        {
            "period": period,
            "label": STATS_PERIODS[period],
            "start_date": start_date,
            "end_date": end_date,
            **data,
        }
    )


@api_errors
async def get_activities(request: web.Request) -> web.Response:
    from coros.models import DateActivityFilter
    from coros.services import ActivityService, AuthService
    from coros.services.auth import CorosAuthError
    from telegram.utils import (
        format_distance,
        format_duration,
        get_coros_sport_emoji_label,
        local_now,
    )

    try:
        days = min(max(int(request.query.get("days", 7)), 1), 31)
    except ValueError:
        return json_error(400, "bad_request", "days must be an integer")

    profile = request["user_ctx"].profile
    coros_config = request["user_ctx"].coros_config

    access_token = await asyncio.to_thread(
        AuthService(coros_config).get_or_set_access_token
    )
    if not access_token:
        raise CorosAuthError(f"Coros auth failed for {profile.coros_email}")

    now = local_now()
    date_filters = DateActivityFilter(
        start_date=(now - timedelta(days=days - 1)).strftime("%Y%m%d"),
        end_date=now.strftime("%Y%m%d"),
    )
    activities = await asyncio.to_thread(
        ActivityService(coros_config).get_activities, date_filters
    )

    items = []
    for activity in sorted(activities, key=lambda a: a.date, reverse=True):
        emoji, type_label = get_coros_sport_emoji_label(activity.sport_type)
        date_str = str(activity.date)
        items.append(
            {
                "date": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
                "name": activity.name or type_label,
                "emoji": emoji,
                "type_label": type_label,
                "distance_text": format_distance(activity.distance),
                "duration_text": format_duration(activity.duration),
            }
        )

    return web.json_response({"activities": items})


def register_api_routes(app: web.Application) -> None:
    app.router.add_get("/api/me", get_me)
    app.router.add_get("/api/stats", get_stats)
    app.router.add_get("/api/activities", get_activities)
