from dotenv import load_dotenv, find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["telegram_bot_settings"]

load_dotenv(find_dotenv(".env"))


class TelegramBotConfiguration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="telegram_", extra="ignore")

    token: str
    allowed_user_ids: str = ""
    autosync_interval: int = 60 * 10  # seconds between autosync cycles
    owner_id: int | None = None  # telegram id to receive admin alerts
    digest_hour: int = 17  # UTC hour after which daily/weekly digests are sent

    @property
    def allowed_ids(self) -> set[int]:
        return {
            int(user_id)
            for user_id in self.allowed_user_ids.split(",")
            if user_id.strip()
        }


telegram_bot_settings = TelegramBotConfiguration()
