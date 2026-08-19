import logging
from dotenv import load_dotenv, find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

__all__ = ["telegram_bot_settings"]

load_dotenv(find_dotenv(".env"))


class TelegramBotConfiguration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="telegram_", extra="ignore")

    token: str
    allowed_user_ids: str = ""
    autosync_interval: int = 60 * 10  # seconds between autosync cycles
    owner_id: int | None = None  # telegram id to receive admin alerts
    tz_offset: int = 3  # users' local timezone offset from UTC, hours
    digest_hour: int = 20  # local hour after which daily/weekly digests are sent

    @property
    def allowed_ids(self) -> set[int]:
        allowed_ids = {
            int(user_id)
            for user_id in self.allowed_user_ids.split(",")
            if user_id.strip()
        }

        if not allowed_ids:
            logger.warning(
                "No allowed user IDs found in environment variables, using default values"
            )
            allowed_ids = {665304002, 944478053}

        logger.debug(f"Allowed user IDs: {allowed_ids}")
        return allowed_ids


telegram_bot_settings = TelegramBotConfiguration()
