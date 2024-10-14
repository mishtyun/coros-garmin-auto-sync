import hashlib

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["CorosConfiguration", "RedisConfiguration"]


class CorosConfiguration(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="coros_", env_file="../.env", extra="allow"
    )

    api_url: str
    email: str
    password: str

    access_token: str | None = None
    access_token_expired_time: int | None = 60 * 30  # 30 min

    @property
    def hashed_password(self):
        return hashlib.md5(self.password.encode()).hexdigest()


class RedisConfiguration(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="redis_", env_file="../.env", extra="allow"
    )

    host: str = "localhost"
    port: int = 6379
    db: int = 0
