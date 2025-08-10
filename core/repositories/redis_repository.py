from typing import Any

from redis import ConnectionPool, Redis

from core.repositories import Repository

__all__ = ["get_redis_client", "RedisRepository", "get_redis_repository"]


def get_redis_client() -> Redis:
    from core.configuration import redis_configuration

    pool = ConnectionPool.from_url(redis_configuration.get_url())
    return Redis(connection_pool=pool)


class RedisRepository(Repository):

    def __init__(self, redis: Redis, expired_time: int | None = None):
        self.redis = redis
        self._expired_time = expired_time

    def get(self, key: str) -> Any:
        if value := self.redis.get(key):
            return value.decode()
        return None

    def set(self, key: str, value: str, set_ex_time: bool = False) -> Any:
        return self.redis.set(
            key, value, ex=self._expired_time if set_ex_time else None
        )


def get_redis_repository(**kwargs) -> RedisRepository:
    redis_client = get_redis_client()
    return RedisRepository(redis=redis_client, **kwargs)
