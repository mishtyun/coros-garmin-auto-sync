import logging
import os
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)

__all__ = ["create_web_app", "start_web_server"]

# mini app frontend lives inside the package — NOT in the repo-level static/
# dir, which the sync flow uses as a scratch area for users' activity files
WEBAPP_STATIC = Path(__file__).parent / "static"


async def health(request: web.Request) -> web.Response:
    # keep-alive endpoint: Render port detection + UptimeRobot pings
    return web.Response(text="OK")


async def webapp_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBAPP_STATIC / "index.html")


async def no_store_on_webapp(request: web.Request, response: web.StreamResponse):
    # no-build-step frontend: never let Telegram's webview cache stale JS
    if request.path.startswith("/webapp"):
        response.headers["Cache-Control"] = "no-store"


def create_web_app() -> web.Application:
    # imported lazily: webapp must not pull in the telegram package at module
    # level (telegram.app imports webapp -> circular import)
    from telegram.configuration import telegram_bot_settings
    from webapp.api import register_api_routes
    from webapp.auth import init_data_middleware

    # the mini app (middleware + api + static) is feature-flagged; the server
    # itself always runs — it binds the Render port and serves the keep-alive
    # endpoint
    webapp_enabled = telegram_bot_settings.webapp_enabled

    app = web.Application(middlewares=[init_data_middleware] if webapp_enabled else [])
    app.router.add_get("/", health)

    if webapp_enabled:
        register_api_routes(app)
        app.router.add_get("/webapp", webapp_index)
        app.router.add_static("/webapp/", WEBAPP_STATIC, show_index=False)
        app.on_response_prepare.append(no_store_on_webapp)
        logger.info("Mini app routes enabled")

    return app


async def start_web_server(port: int | None = None) -> web.AppRunner:
    if port is None:
        port = int(os.environ.get("PORT", 8080))

    runner = web.AppRunner(create_web_app())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"Web server started on port {port}")
    return runner
