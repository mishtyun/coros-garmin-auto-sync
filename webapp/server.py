import logging
import os

from aiohttp import web

logger = logging.getLogger(__name__)

__all__ = ["create_web_app", "start_web_server"]


async def health(request: web.Request) -> web.Response:
    # keep-alive endpoint: Render port detection + UptimeRobot pings
    return web.Response(text="OK")


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", health)
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
