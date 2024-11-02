from aiogram import types, Router

__all__ = ["router"]

router = Router()


@router.message()
async def cmd_start(message: types.Message):
    await message.answer("Hey!", reply_markup=types.ReplyKeyboardRemove())
