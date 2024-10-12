from typing import Any

from redis import Redis, ConnectionPool

from coros.repositories import Repository

__all__ = ["RedisRepository", "get_redis_repository"]


def get_redis_client() -> Redis:
    from coros.app import redis_configuration

    pool = ConnectionPool(
        host=redis_configuration.host,
        port=redis_configuration.port,
        db=redis_configuration.db,
    )
    return Redis(connection_pool=pool)


class RedisRepository(Repository):

    def __init__(self, redis: Redis):
        self.redis = redis

    def get(self, key: str) -> Any:
        if value := self.redis.get(key):
            return value.decode()
        return None

    def add_access_token(self, key: str, access_token: str) -> bool:
        return self.redis.set(key, access_token)

    def flush(self):
        return self.redis.flushdb()


def get_redis_repository() -> RedisRepository:
    redis_client = get_redis_client()
    return RedisRepository(redis_client)
