from core.logger import setup_logger
from telegram import run_bot
from web import run_web

logger = setup_logger()


if __name__ == "__main__":
    run_bot()
    run_web()
