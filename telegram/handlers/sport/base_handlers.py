import logging

from aiogram import F, Router, types

from telegram.keyboards import get_sport_action_keyboard

logger = logging.getLogger(__name__)

START_HANDLER_COMMAND = "/sport"

__all__ = ["router"]

router = Router()


@router.message(F.text == START_HANDLER_COMMAND)
async def sport_cmd_start(message: types.Message):
    logger.info("Starting sport command")
    keyboard = get_sport_action_keyboard()

    await message.answer("🏊‍♂️🏃‍♂️🚴‍♀️ Hey athlete!", reply_markup=keyboard)
    logger.info("Sport command keyboard sent")
