import asyncio
import logging

from aiogram import F, Router, types
from aiogram.types import BufferedInputFile

from coros.services import ActivityService, AuthService
from telegram.keyboards import SportActionCallbacks
from telegram.utils import upload_and_get_url
from users.context import UserContext

logger = logging.getLogger(__name__)

__all__ = ["latests_router"]

latests_router = Router()


@latests_router.callback_query(F.data == SportActionCallbacks.DOWNLOAD_LATEST)
async def download_latest_activity_button_handler(
    callback_query: types.CallbackQuery, user_ctx: UserContext
):
    logger.info("Downloading latest activity")
    await callback_query.answer()
    try:
        coros_config = user_ctx.coros_config
        await asyncio.to_thread(AuthService(coros_config).get_or_set_access_token)

        activity_name, activity_content = await asyncio.to_thread(
            ActivityService(coros_config).get_latest_activity_bytes
        )

        if not activity_name or not activity_content:
            logger.info("Latest activity not found")
            await callback_query.message.answer("Latest activity not found")
            return

        activity_file = BufferedInputFile(
            filename=activity_name, file=activity_content.read()
        )

        await callback_query.message.answer_document(
            document=activity_file, caption="Latest activity"
        )
        logger.info(
            f"Successfully downloaded and sent latest activity: {activity_name}"
        )
    except Exception as e:
        logger.error(
            f"Error while downloading latest activity: {str(e)}", exc_info=True
        )
        await callback_query.message.answer("Error while downloading")


@latests_router.callback_query(F.data == SportActionCallbacks.SYNC_LATEST)
async def sync_latest_activity_button_handler(
    callback_query: types.CallbackQuery, user_ctx: UserContext
):
    logger.info("Syncing latest activity")
    await callback_query.answer()
    try:
        coros_config = user_ctx.coros_config
        await asyncio.to_thread(AuthService(coros_config).get_or_set_access_token)
        activity_name, activity_content = await asyncio.to_thread(
            ActivityService(coros_config).get_latest_activity_bytes
        )

        garmin_api = await user_ctx.get_garmin()
        is_uploaded, garmin_activity_link, activity_title = await upload_and_get_url(
            garmin_api, file_name=activity_name, file=activity_content
        )

        status_text = "Synced successfully! ✅" if is_uploaded else "Already synced :)"
        message_to_answer = (
            f'{status_text}\n<a href="{garmin_activity_link}">{activity_title}</a>'
        )

        await callback_query.message.answer(
            message_to_answer,
            parse_mode="HTML",
            link_preview_options=types.LinkPreviewOptions(is_disabled=True),
        )
        logger.info(f"Successfully synced latest activity: {garmin_activity_link}")
    except Exception as e:
        logger.error(f"Error while syncing latest activity: {str(e)}", exc_info=True)
        await callback_query.message.answer("Error while syncing")
