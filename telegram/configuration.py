from dotenv import load_dotenv, find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["telegram_bot_settings"]

load_dotenv(find_dotenv(".env"))


class TelegramBotConfiguration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="telegram_", extra="ignore")

    token: str


telegram_bot_settings = TelegramBotConfiguration()
