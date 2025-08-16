import logging

from aiogram import F, Router, types
from aiogram.types import BufferedInputFile

from coros import coros_configuration
from coros.services import ActivityService, AuthService
from telegram.handlers.sport.core import garmin_api
from telegram.keyboards import SportActionButtons
from telegram.utils import upload_and_get_url

logger = logging.getLogger(__name__)

__all__ = ["latests_router"]

latests_router = Router()


@latests_router.message(F.text == SportActionButtons.DOWNLOAD_LATEST)
async def download_latest_activity_button_handler(message: types.Message):
    logger.info("Downloading latest activity")
    try:
        AuthService(coros_configuration).get_or_set_access_token()

        activity_name, activity_content = ActivityService(
            coros_configuration
        ).get_latest_activity_bytes()

        if not activity_name or not activity_content:
            logger.info("Latest activity not found")
            await message.answer("Latest activity not found")
            return

        activity_file = BufferedInputFile(
            filename=activity_name, file=activity_content.read()
        )

        await message.reply_document(document=activity_file, caption="Latest activity")
        logger.info(
            f"Successfully downloaded and sent latest activity: {activity_name}"
        )
    except Exception as e:
        logger.error(
            f"Error while downloading latest activity: {str(e)}", exc_info=True
        )
        await message.answer("Error while downloading")


@latests_router.message(F.text == SportActionButtons.SYNC_LATEST)
async def sync_latest_activity_button_handler(message: types.Message):
    logger.info("Syncing latest activity")
    try:
        AuthService(coros_configuration).get_or_set_access_token()
        activity_name, activity_content = ActivityService(
            coros_configuration
        ).get_latest_activity_bytes()

        is_uploaded, garmin_activity_link = await upload_and_get_url(
            garmin_api, file_name=activity_name, file=activity_content
        )

        message_to_answer = (
            f"Synced successfully!\n{garmin_activity_link}"
            if is_uploaded
            else f"Already synced :)\n{garmin_activity_link}"
        )

        await message.reply(message_to_answer)
        logger.info(f"Successfully synced latest activity: {garmin_activity_link}")
    except Exception as e:
        logger.error(f"Error while syncing latest activity: {str(e)}", exc_info=True)
        await message.answer("Error while syncing")
