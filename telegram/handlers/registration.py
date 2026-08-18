import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from coros.configuration import CorosConfiguration
from coros.repositories.redis_repository import get_coros_redis_repository
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


@registration_router.message(Command("status"))
async def status_cmd(message: types.Message):
    profile = get_user_redis_repository().get_profile(message.from_user.id)
    if not profile:
        await message.answer("You're not registered yet — send /register")
        return

    coros_repository = get_coros_redis_repository()

    if coros_repository.get_access_token(profile.coros_email):
        coros_status = "✅ session active"
    else:
        configuration = CorosConfiguration(
            email=profile.coros_email, password_md5=profile.coros_password_md5
        )
        try:
            access_token = await asyncio.to_thread(
                AuthService(configuration).send_login_request, True
            )
        except Exception as e:
            logger.error(f"Coros status check failed: {e}")
            access_token = None
        coros_status = (
            "✅ login ok" if access_token else "❌ auth failed — update via /register"
        )

    oauth_data = get_user_redis_repository().get_garmin_oauth(message.from_user.id)
    if not oauth_data:
        garmin_status = "❌ not linked — run /register"
    else:
        expires_at = oauth_data.get("oauth2", {}).get("expires_at")
        if expires_at and float(expires_at) > datetime.now(timezone.utc).timestamp():
            valid_until = datetime.fromtimestamp(float(expires_at), tz=timezone.utc)
            garmin_status = (
                f"✅ session stored, valid until {valid_until:%Y-%m-%d %H:%M} UTC"
            )
        else:
            garmin_status = "✅ session stored (will refresh on next sync)"

    autosync_status = get_autosync_mode_text(profile).removeprefix("Autosync: ")

    last_sync_data = coros_repository.get_latest_activity_data(profile.coros_email)
    if last_sync_data and last_sync_data.get("synced_at"):
        last_sync = f"{last_sync_data.get('name')} at {last_sync_data['synced_at']}"
    elif last_sync_data:
        last_sync = f"{last_sync_data.get('name')} (baseline)"
    else:
        last_sync = "—"

    await message.answer(
        f"📋 Status:\n"
        f"Coros: {coros_status}\n"
        f"Garmin: {garmin_status}\n"
        f"Autosync: {autosync_status}\n"
        f"Last sync: {last_sync}"
    )


def get_autosync_mode_text(profile: UserProfile) -> str:
    if profile.autosync and profile.autosync_quiet:
        mode = "🔕 ON (quiet — no notifications)"
    elif profile.autosync:
        mode = "🔔 ON — you'll get a message for every synced workout"
    else:
        mode = "⏸ OFF"
    return f"Autosync: {mode}"


def get_autosync_keyboard() -> types.InlineKeyboardMarkup:
    kb = [
        [
            types.InlineKeyboardButton(text="🔔 On", callback_data="autosync:on"),
            types.InlineKeyboardButton(
                text="🔕 On (quiet)", callback_data="autosync:quiet"
            ),
            types.InlineKeyboardButton(text="⏸ Off", callback_data="autosync:off"),
        ]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=kb)


@registration_router.message(Command("autosync"))
async def autosync_cmd(message: types.Message):
    profile = get_user_redis_repository().get_profile(message.from_user.id)
    if not profile:
        await message.answer("You're not registered yet — send /register")
        return

    await message.answer(
        f"{get_autosync_mode_text(profile)}\n\n"
        "New workouts appear in Garmin within ~10 minutes "
        "after your watch syncs with the Coros app.",
        reply_markup=get_autosync_keyboard(),
    )


@registration_router.callback_query(F.data.startswith("autosync:"))
async def autosync_mode_callback(callback_query: types.CallbackQuery):
    repository = get_user_redis_repository()
    profile = repository.get_profile(callback_query.from_user.id)
    if not profile:
        await callback_query.answer("You're not registered yet — send /register")
        return

    mode = callback_query.data.split(":", 1)[1]
    profile.autosync = mode in ("on", "quiet")
    profile.autosync_quiet = mode == "quiet"
    repository.save_profile(profile)

    try:
        await callback_query.message.edit_text(
            get_autosync_mode_text(profile), reply_markup=get_autosync_keyboard()
        )
    except Exception:
        # same mode pressed twice -> "message is not modified", nothing to update
        pass
    await callback_query.answer("Saved")


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
