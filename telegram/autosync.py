import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import LinkPreviewOptions

from coros.configuration import CorosConfiguration
from coros.models import DateActivityFilter
from coros.repositories.redis_repository import get_coros_redis_repository
from coros.services import ActivityService, AuthService
from garmin.client import GarminSessionExpiredError, garmin_client_cache
from telegram.configuration import telegram_bot_settings
from telegram.utils import upload_and_get_url
from users.models import UserProfile
from users.repository import get_user_redis_repository

logger = logging.getLogger(__name__)

__all__ = ["autosync_loop"]

COROS_DATE_FORMAT = "%Y%m%d"


async def _disable_autosync(bot: Bot, profile: UserProfile, reason: str) -> None:
    profile.autosync = False
    get_user_redis_repository().save_profile(profile)
    await bot.send_message(profile.tg_id, f"⏸ Autosync disabled: {reason}")


async def _sync_user(bot: Bot, profile: UserProfile) -> None:
    coros_config = CorosConfiguration(
        email=profile.coros_email, password_md5=profile.coros_password_md5
    )
    coros_repository = get_coros_redis_repository(
        expired_time=coros_config.access_token_expired_time
    )

    access_token = await asyncio.to_thread(
        AuthService(coros_config).get_or_set_access_token
    )
    if not access_token:
        await _disable_autosync(
            bot,
            profile,
            "Coros auth failed — update credentials via /register, then /autosync",
        )
        return

    latest_activity = await asyncio.to_thread(
        ActivityService(coros_config).get_latest_activity
    )
    if not latest_activity:
        return

    baseline = coros_repository.get_latest_activity_data(coros_config.email)
    if baseline and baseline.get("label_id") == latest_activity.label_id:
        return

    if baseline is None:
        # first cycle after enabling: remember the current latest activity
        # and only sync workouts recorded after it
        coros_repository.add_latest_activity_data(
            coros_config.email, latest_activity.model_dump()
        )
        return

    garmin_api = await garmin_client_cache.get_or_create(
        profile.tg_id, profile.garmin_email
    )

    now = datetime.now()
    date_filters = DateActivityFilter(
        start_date=(now - timedelta(1)).strftime(COROS_DATE_FORMAT),
        end_date=now.strftime(COROS_DATE_FORMAT),
    )
    files = await asyncio.to_thread(
        ActivityService(coros_config).get_daily_activities_bytes, date_filters
    )

    synced_links = []
    for file_name, file_content in files:
        uploaded, link, title = await upload_and_get_url(
            garmin_api, file_name=file_name, file=file_content
        )
        if uploaded and link:
            synced_links.append(f'<a href="{link}">{title}</a>')

    coros_repository.add_latest_activity_data(
        coros_config.email,
        {
            **latest_activity.model_dump(),
            "synced_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    if synced_links:
        logger.info(
            f"Auto-synced {len(synced_links)} activities for tg_id={profile.tg_id}"
        )
        if not profile.autosync_quiet:
            links_text = "\n".join(synced_links)
            await bot.send_message(
                profile.tg_id,
                f"✅ Auto-synced to Garmin:\n{links_text}",
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )


async def run_autosync_cycle(bot: Bot) -> None:
    profiles = await asyncio.to_thread(get_user_redis_repository().get_all_profiles)

    for profile in profiles:
        if not profile.autosync:
            continue

        try:
            await _sync_user(bot, profile)
        except GarminSessionExpiredError:
            await _disable_autosync(
                bot,
                profile,
                "Garmin session expired — relink via /register, then /autosync",
            )
        except Exception as e:
            # transient errors (network etc.): keep autosync enabled, retry next cycle
            logger.error(
                f"Autosync failed for tg_id={profile.tg_id}: {e}", exc_info=True
            )


async def autosync_loop(bot: Bot) -> None:
    interval = telegram_bot_settings.autosync_interval
    logger.info(f"Autosync loop started, interval={interval}s")

    while True:
        try:
            await run_autosync_cycle(bot)
        except Exception as e:
            logger.error(f"Autosync cycle failed: {e}", exc_info=True)

        await asyncio.sleep(interval)
