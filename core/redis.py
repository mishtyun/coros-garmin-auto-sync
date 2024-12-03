from typing import Protocol

from pydantic_settings import BaseSettings, SettingsConfigDict
from redis import Redis, ConnectionPool


__all__ = ["get_redis_client", "get_redis_client_with_default_config"]


class IRedisConfig(Protocol):
    @property
    def connection_url(self) -> int:
        raise NotImplementedError


class RedisConfiguration(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="redis_", extra="ignore")

    url: str | None = None
    host: str = "localhost"
    port: int = 6379
    db: int = 0

    @property
    def connection_url(self):
        return (
            f"redis://{self.host}:{self.port}/{self.db}"
            if self.url is None
            else self.url
        )


redis_configuration = RedisConfiguration()


def get_redis_client(redis_config: IRedisConfig) -> Redis:
    pool = ConnectionPool.from_url(redis_config.connection_url)
    return Redis(connection_pool=pool)


def get_redis_client_with_default_config() -> Redis:
    pool = ConnectionPool.from_url(redis_configuration.connection_url)
    return Redis(connection_pool=pool)
