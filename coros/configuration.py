import hashlib
import os

from dotenv import load_dotenv, find_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "BASE_DIR",
    "STATIC_ROOT",
    "coros_configuration",
    "CorosConfiguration",
]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_ROOT = os.path.join(BASE_DIR, "static")

load_dotenv(find_dotenv(".env"))


class CorosConfiguration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="coros_", extra="ignore")

    api_url: str = Field(default="https://teameapi.coros.com")
    email: str
    password: str

    access_token: str | None = None
    access_token_expired_time: int | None = 60 * 30  # 30 min

    @property
    def hashed_password(self):
        return hashlib.md5(self.password.encode()).hexdigest()


coros_configuration = CorosConfiguration()
