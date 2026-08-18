import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, types

from telegram.configuration import telegram_bot_settings
from users.context import UserContext
from users.repository import get_user_redis_repository

logger = logging.getLogger(__name__)

__all__ = ["UserContextMiddleware"]


async def _reply(event: types.TelegramObject, text: str) -> None:
    if isinstance(event, types.CallbackQuery):
        await event.answer(text, show_alert=True)
    elif isinstance(event, types.Message):
        await event.answer(text)


class UserContextMiddleware(BaseMiddleware):
    """Injects `user_ctx` into sport handlers; rejects unknown users.

    Registered as an inner middleware, so it only runs when a handler
    in the sport router actually matched.
    """

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        if not from_user:
            return await handler(event, data)

        tg_id = from_user.id

        if tg_id not in telegram_bot_settings.allowed_ids:
            logger.info(f"Rejected sport action from tg_id={tg_id}")
            await _reply(event, "Sorry, this bot is private.")
            return None

        profile = get_user_redis_repository().get_profile(tg_id)
        if not profile:
            await _reply(event, "You're not registered yet — send /register")
            return None

        data["user_ctx"] = UserContext(tg_id=tg_id, profile=profile)
        return await handler(event, data)
