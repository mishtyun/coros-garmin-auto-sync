import hashlib

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["CorosConfiguration"]


class CorosConfiguration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="coros_", extra="ignore")

    api_url: str = Field(default="https://teameapi.coros.com")
    email: str
    password: str | None = None
    password_md5: str | None = None

    access_token: str | None = None
    access_token_expired_time: int | None = 60 * 30  # 30 min

    @property
    def hashed_password(self) -> str | None:
        if self.password_md5:
            return self.password_md5
        if self.password:
            return hashlib.md5(self.password.encode()).hexdigest()
        return None
