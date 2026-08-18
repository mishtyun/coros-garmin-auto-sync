import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from aiogram import Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from coros.configuration import CorosConfiguration
from coros.services import AuthService
from garmin.client import GarminMFARequiredError, garmin_client_cache
from garmin.client import login_with_credentials
from telegram.configuration import telegram_bot_settings
from telegram.states.registration import RegistrationStates
from users.models import UserProfile
from users.repository import get_user_redis_repository

logger = logging.getLogger(__name__)

__all__ = ["registration_router"]

registration_router = Router()


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    masked_name = name[0] + "***" if name else "***"
    return f"{masked_name}@{domain}"


async def delete_password_message(message: types.Message) -> None:
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Can't delete password message: {e}")
        await message.answer(
            "⚠️ I couldn't delete your message — please delete it manually."
        )


@registration_router.message(Command("register"))
async def register_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id not in telegram_bot_settings.allowed_ids:
        logger.info(f"Rejected /register from tg_id={message.from_user.id}")
        await message.answer("Sorry, this bot is private.")
        return

    await state.set_state(RegistrationStates.coros_email)
    await message.answer(
        "Let's link your accounts.\n\nSend your Coros email (or /cancel to abort)"
    )


@registration_router.message(Command("cancel"), StateFilter(RegistrationStates))
async def cancel_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Registration cancelled.")


@registration_router.message(Command("settings"))
async def settings_cmd(message: types.Message):
    profile = get_user_redis_repository().get_profile(message.from_user.id)
    if not profile:
        await message.answer("You're not registered yet — send /register")
        return

    await message.answer(
        f"Linked accounts:\n"
        f"Coros: {mask_email(profile.coros_email)}\n"
        f"Garmin: {mask_email(profile.garmin_email)}\n\n"
        f"Re-run /register to update credentials, /unlink to remove them."
    )


@registration_router.message(Command("unlink"))
async def unlink_cmd(message: types.Message):
    tg_id = message.from_user.id
    get_user_redis_repository().delete_user(tg_id)
    garmin_client_cache.evict(tg_id)
    await message.answer("Your accounts are unlinked and data removed.")


@registration_router.message(StateFilter(RegistrationStates.coros_email))
async def process_coros_email(message: types.Message, state: FSMContext):
    await state.update_data(coros_email=message.text.strip())
    await state.set_state(RegistrationStates.coros_password)
    await message.answer("Send your Coros password (the message will be deleted)")


@registration_router.message(StateFilter(RegistrationStates.coros_password))
async def process_coros_password(message: types.Message, state: FSMContext):
    password = message.text
    await delete_password_message(message)

    data = await state.get_data()
    password_md5 = hashlib.md5(password.encode()).hexdigest()
    configuration = CorosConfiguration(
        email=data["coros_email"], password_md5=password_md5
    )

    try:
        access_token = await asyncio.to_thread(
            AuthService(configuration).send_login_request, True
        )
    except Exception as e:
        logger.error(f"Coros login request failed: {e}", exc_info=True)
        access_token = None

    if not access_token:
        await message.answer("Coros login failed — send the password again, or /cancel")
        return

    await state.update_data(coros_password_md5=password_md5)
    await state.set_state(RegistrationStates.garmin_email)
    await message.answer("Coros linked ✅\n\nNow send your Garmin email")


@registration_router.message(StateFilter(RegistrationStates.garmin_email))
async def process_garmin_email(message: types.Message, state: FSMContext):
    await state.update_data(garmin_email=message.text.strip())
    await state.set_state(RegistrationStates.garmin_password)
    await message.answer("Send your Garmin password (the message will be deleted)")


@registration_router.message(StateFilter(RegistrationStates.garmin_password))
async def process_garmin_password(message: types.Message, state: FSMContext):
    password = message.text
    await delete_password_message(message)

    tg_id = message.from_user.id
    data = await state.get_data()

    try:
        await asyncio.to_thread(
            login_with_credentials, tg_id, data["garmin_email"], password
        )
    except GarminMFARequiredError:
        await message.answer(
            "Garmin accounts with MFA/2FA aren't supported yet. "
            "Disable MFA and send the password again, or /cancel"
        )
        return
    except Exception as e:
        logger.error(f"Garmin login failed: {e}", exc_info=True)
        await message.answer(
            "Garmin login failed — send the password again, or /cancel"
        )
        return

    profile = UserProfile(
        tg_id=tg_id,
        coros_email=data["coros_email"],
        coros_password_md5=data["coros_password_md5"],
        garmin_email=data["garmin_email"],
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    get_user_redis_repository().save_profile(profile)
    garmin_client_cache.evict(tg_id)

    await state.clear()
    await message.answer("You're all set 🎉 Try /sport")
