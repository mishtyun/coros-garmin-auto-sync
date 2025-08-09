from aiogram import types, F, Router


__all__ = ["router"]


START_HANDLER_COMMAND = "/todo"

router = Router()


@router.message(F.text == START_HANDLER_COMMAND)
async def cmd_start(message: types.Message):
    # print current to-do list
    await message.answer(
        "Send message to create ToDo!", reply_markup=types.ReplyKeyboardRemove()
    )
