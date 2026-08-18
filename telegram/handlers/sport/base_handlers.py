import logging

from aiogram import Router, types
from aiogram.filters import Command

from telegram.keyboards import get_sport_action_inline_keyboard

logger = logging.getLogger(__name__)

__all__ = ["router"]

router = Router()


@router.message(Command("sport"))
async def sport_cmd_start(message: types.Message):
    logger.info("Starting sport command")
    keyboard = get_sport_action_inline_keyboard()

    await message.answer("🏊‍♂️🏃‍♂️🚴‍♀️ Hey athlete!", reply_markup=keyboard)
    logger.info("Sport command keyboard sent")
