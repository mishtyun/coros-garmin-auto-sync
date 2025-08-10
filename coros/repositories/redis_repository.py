import json

from core.repositories.redis_repository import RedisRepository, get_redis_client

__all__ = ["CorosRedisRepository", "get_coros_redis_repository"]


class CorosRedisRepository(RedisRepository):
    def add_access_token(self, key: str, access_token: str) -> bool:
        return self.set(key, access_token, set_ex_time=True)

    def add_latest_activity_data(self, activity_data: dict) -> bool:
        return self.set("latest_activity", json.dumps(activity_data))

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


def get_coros_redis_repository(**kwargs) -> CorosRedisRepository:
    redis_client = get_redis_client()
    return CorosRedisRepository(redis=redis_client, **kwargs)
