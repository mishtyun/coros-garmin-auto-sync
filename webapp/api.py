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


@api_errors
async def post_sync_today(request: web.Request) -> web.Response:
    from telegram.utils import local_now, sync_activities_by_dates

    user_ctx = request["user_ctx"]
    garmin_api = await user_ctx.get_garmin()

    today = local_now().strftime("%Y%m%d")
    results = await sync_activities_by_dates(
        garmin_api, user_ctx.coros_config, today, today
    )

    synced = [
        {"title": title, "url": url} for uploaded, url, title in results if uploaded
    ]
    already_synced = sum(1 for uploaded, url, _ in results if url and not uploaded)

    return web.json_response({"synced": synced, "already_synced": already_synced})


@api_errors
async def post_sync_latest(request: web.Request) -> web.Response:
    from telegram.utils import sync_latest_activity

    user_ctx = request["user_ctx"]
    garmin_api = await user_ctx.get_garmin()

    result = await sync_latest_activity(garmin_api, user_ctx.coros_config)
    if result is None:
        return web.json_response({"latest": None})

    uploaded, url, title = result
    return web.json_response(
        {"latest": {"title": title, "url": url, "uploaded": uploaded}}
    )


SETTINGS_KEYS = {"autosync", "autosync_quiet", "digest"}


@api_errors
async def post_settings(request: web.Request) -> web.Response:
    from users.repository import get_user_redis_repository

    try:
        body = await request.json()
    except Exception:
        return json_error(400, "bad_request", "Invalid JSON body")

    if not isinstance(body, dict) or not body:
        return json_error(400, "bad_request", "Body must be a non-empty object")

    unknown = set(body) - SETTINGS_KEYS
    if unknown:
        return json_error(400, "bad_request", f"Unknown keys: {sorted(unknown)}")
    if not all(isinstance(value, bool) for value in body.values()):
        return json_error(400, "bad_request", "Values must be booleans")

    repository = get_user_redis_repository()
    profile = repository.get_profile(request["user_ctx"].tg_id)
    for key, value in body.items():
        setattr(profile, key, value)
    repository.save_profile(profile)

    return web.json_response(me_payload(profile))


def register_api_routes(app: web.Application) -> None:
    app.router.add_get("/api/me", get_me)
    app.router.add_get("/api/stats", get_stats)
    app.router.add_get("/api/activities", get_activities)
    app.router.add_post("/api/sync/today", post_sync_today)
    app.router.add_post("/api/sync/latest", post_sync_latest)
    app.router.add_post("/api/settings", post_settings)
