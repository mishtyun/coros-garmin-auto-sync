import logging

from aiogram import F, Router, types
from aiogram.filters import Command

from telegram.keyboards import (
    SportActionCallbacks,
    get_sport_action_inline_keyboard,
    get_sport_more_inline_keyboard,
)

logger = logging.getLogger(__name__)

__all__ = ["router"]

router = Router()


@router.message(Command("sport"))
async def sport_cmd_start(message: types.Message):
    logger.info("Starting sport command")
    keyboard = get_sport_action_inline_keyboard()

    await message.answer("🏊‍♂️🏃‍♂️🚴‍♀️ Hey athlete!", reply_markup=keyboard)
    logger.info("Sport command keyboard sent")


@router.callback_query(F.data == SportActionCallbacks.MORE)
async def sport_more_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_reply_markup(
        reply_markup=get_sport_more_inline_keyboard()
    )
    await callback_query.answer()


@router.callback_query(F.data == SportActionCallbacks.MENU)
async def sport_main_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_reply_markup(
        reply_markup=get_sport_action_inline_keyboard()
    )
    await callback_query.answer()
