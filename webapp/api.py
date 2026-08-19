import functools
import logging

from aiohttp import web

from webapp.auth import json_error

logger = logging.getLogger(__name__)

__all__ = ["register_api_routes"]


def api_errors(handler):
    from garmin.client import GarminMFARequiredError, GarminSessionExpiredError

    @functools.wraps(handler)
    async def wrapper(request: web.Request) -> web.StreamResponse:
        try:
            return await handler(request)
        except (GarminSessionExpiredError, GarminMFARequiredError):
            return json_error(
                409,
                "garmin_session_expired",
                "Garmin session expired — re-register in the bot chat (/register).",
            )
        except CorosAuthError:
            return json_error(
                409,
                "coros_auth_failed",
                "Coros login failed — re-register in the bot chat (/register).",
            )
        except Exception as e:
            logger.error(f"API error in {handler.__name__}: {e}", exc_info=True)
            return json_error(
                500, "internal", "Something went wrong — try again later."
            )

    return wrapper


class CorosAuthError(Exception):
    """Raised when the Coros access token can't be obtained."""


def me_payload(profile) -> dict:
    return {
        "tg_id": profile.tg_id,
        "coros_email": profile.coros_email,
        "garmin_email": profile.garmin_email,
        "autosync": profile.autosync,
        "autosync_quiet": profile.autosync_quiet,
        "digest": profile.digest,
        "created_at": profile.created_at,
    }


@api_errors
async def get_me(request: web.Request) -> web.Response:
    return web.json_response(me_payload(request["user_ctx"].profile))


def register_api_routes(app: web.Application) -> None:
    app.router.add_get("/api/me", get_me)
