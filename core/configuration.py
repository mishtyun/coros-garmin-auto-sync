import os

from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "BASE_DIR",
    "STATIC_ROOT",
    "redis_configuration",
    "RedisConfiguration",
]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_ROOT = os.path.join(BASE_DIR, "static")

load_dotenv(find_dotenv(".env"))


class RedisConfiguration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="redis_", extra="ignore")

    url: str | None = None
    host: str = "localhost"
    port: int = 6379
    db: int = 0

    def get_url(self):
        return (
            f"redis://{self.host}:{self.port}/{self.db}"
            if self.url is None
            else self.url
        )


redis_configuration = RedisConfiguration()
