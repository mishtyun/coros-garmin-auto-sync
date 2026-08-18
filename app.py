from core.logger import setup_logger
from telegram import run_bot
from web import run_web

logger = setup_logger()


if __name__ == "__main__":
    # cherrypy engine.start() is non-blocking; run_bot() blocks on polling,
    # so the web server (Render port binding) must start first
    run_web()
    run_bot()
