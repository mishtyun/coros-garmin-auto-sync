import hashlib

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["coros_configuration", "CorosConfiguration"]


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
