import logging
from datetime import datetime, timedelta, timezone

from aiogram.utils.web_app import safe_parse_webapp_init_data
from aiohttp import web

from telegram.configuration import telegram_bot_settings
from users.context import UserContext
from users.repository import get_user_redis_repository

logger = logging.getLogger(__name__)

__all__ = ["init_data_middleware", "json_error"]

# initData is minted once when the Mini App opens and never refreshed,
# so allow a dashboard left open for a while; the bot is allow-listed anyway
AUTH_MAX_AGE = timedelta(hours=24)

INIT_DATA_HEADER = "X-Telegram-Init-Data"


def json_error(status: int, code: str, message: str) -> web.Response:
    return web.json_response(
        {"error": {"code": code, "message": message}}, status=status
    )


@web.middleware
async def init_data_middleware(request: web.Request, handler) -> web.StreamResponse:
    """Validate Telegram WebApp initData for /api/* and inject user_ctx.

    Validation (done by aiogram's safe_parse_webapp_init_data):
    secret = HMAC_SHA256(key=b"WebAppData", msg=bot_token); the received hash
    must equal HMAC_SHA256(secret, "\\n".join(sorted k=v pairs excluding hash)).
    """
    if not request.path.startswith("/api/"):
        return await handler(request)

    init_data = request.headers.get(INIT_DATA_HEADER, "")

    try:
        web_app_data = safe_parse_webapp_init_data(
            telegram_bot_settings.token, init_data
        )
    except ValueError:
        return json_error(
            401, "invalid_init_data", "Open this page from the Telegram bot."
        )

    if datetime.now(timezone.utc) - web_app_data.auth_date > AUTH_MAX_AGE:
        return json_error(401, "invalid_init_data", "Session expired — reopen the app.")

    if not web_app_data.user:
        return json_error(
            401, "invalid_init_data", "Open this page from the Telegram bot."
        )

    tg_id = web_app_data.user.id

    if tg_id not in telegram_bot_settings.allowed_ids:
        logger.info(f"Rejected webapp request from tg_id={tg_id}")
        return json_error(403, "forbidden", "Sorry, this bot is private.")

    profile = get_user_redis_repository().get_profile(tg_id)
    if not profile:
        return json_error(
            403,
            "not_registered",
            "You're not registered yet — send /register in the bot chat.",
        )

    request["user_ctx"] = UserContext(tg_id=tg_id, profile=profile)
    return await handler(request)
