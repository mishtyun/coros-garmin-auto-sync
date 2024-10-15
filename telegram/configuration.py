from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["telegram_bot_settings"]


class TelegramBotConfiguration(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="telegram_", env_file="../.env", extra="allow"
    )

    token: str


# if os.environ.get("IS_HEROKU", None):
#     bot_settings = TelegramBotConfiguration(
#         bot_token=os.environ.get("BOT_TOKEN"),
#     )
# else:
telegram_bot_settings = TelegramBotConfiguration()
