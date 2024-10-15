import json
from typing import Any

from redis import Redis, ConnectionPool

from coros.repositories import Repository

__all__ = ["RedisRepository", "get_redis_repository"]


def get_redis_client() -> Redis:
    from coros.configuration import redis_configuration

    pool = ConnectionPool(
        host=redis_configuration.host,
        port=redis_configuration.port,
        db=redis_configuration.db,
    )
    return Redis(connection_pool=pool)


class RedisRepository(Repository):

    def __init__(self, redis: Redis, expired_time: int | None = None):
        self.redis = redis
        self._expired_time = expired_time

    def get(self, key: str) -> Any:
        if value := self.redis.get(key):
            return value.decode()
        return None

    def add_access_token(self, key: str, access_token: str) -> bool:
        return self.redis.set(key, access_token, ex=self._expired_time)

    def add_latest_activity_data(self, activity_data: dict) -> bool:
        return self.redis.set("latest_activity", json.dumps(activity_data))

    def get_latest_activity_data(self) -> dict | None:
        data_key = "latest_activity"

        activity_data_bytes = self.redis.get(data_key)
        if not activity_data_bytes:
            return None

        if not isinstance(activity_data_bytes, bytes):
            return None

        activity_data_str = activity_data_bytes.decode()
        try:
            return json.loads(activity_data_str)
        except json.JSONDecodeError:
            print(f"Can't parse activity data, for `{data_key}`")
            return None

    def flush(self):
        return self.redis.flushdb()


def get_redis_repository() -> RedisRepository:
    from coros.app import coros_configuration

    redis_client = get_redis_client()
    return RedisRepository(
        redis=redis_client, expired_time=coros_configuration.access_token_expired_time
    )
