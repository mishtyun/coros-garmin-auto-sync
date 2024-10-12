from typing import Any

from redis import Redis, ConnectionPool

from coros.repositories import Repository


class RedisRepository(Repository):

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, **filters: Any) -> Any:
        return None

    async def add_access_key(self, access_key: str) -> bool:
        return False


def get_redis_client() -> Redis:
    pool = ConnectionPool(host="localhost", port=6379, db=0)
    return Redis(connection_pool=pool)


def get_redis_repository() -> RedisRepository:
    redis_client = get_redis_client()
    return RedisRepository(redis_client)
