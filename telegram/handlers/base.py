from aiogram import Router, types
from aiogram.filters import Command

__all__ = ["router"]

router = Router()

HELP_TEXT = (
    "🏊‍♂️🏃‍♂️🚴‍♀️ I sync your workouts from Coros to Garmin Connect.\n"
    "\n"
    "Quick start:\n"
    "1. /register — link your Coros and Garmin accounts\n"
    "2. /sport — sync menu (download / sync latest, daily, by date)\n"
    "3. /autosync — sync new workouts automatically\n"
    "\n"
    "All commands:\n"
    "/register — link or update your accounts\n"
    "/relink_garmin — re-link Garmin only\n"
    "/sport — open the sync menu\n"
    "/plan_workout — plan a workout from text (AI)\n"
    "/autosync — automatic sync settings\n"
    "/stats — workout stats and digests\n"
    "/status — check your Coros/Garmin sessions\n"
    "/settings — show linked accounts\n"
    "/unlink — remove your accounts and data\n"
    "/cancel — abort registration\n"
    "/help — this message"
)


@router.message(Command("start"))
@router.message(Command("help"))
async def help_cmd(message: types.Message):
    # ReplyKeyboardRemove clears the legacy /sport reply keyboard
    # still pinned for users who used the bot before the inline menu
    await message.answer(HELP_TEXT, reply_markup=types.ReplyKeyboardRemove())


@router.message()
async def fallback_cmd(message: types.Message):
    await message.answer(
        "Not sure what you mean 🤔 Try /help",
        reply_markup=types.ReplyKeyboardRemove(),
    )
