import json

from core.repositories.redis_repository import RedisRepository, get_redis_client

__all__ = ["CorosRedisRepository", "get_coros_redis_repository"]


class CorosRedisRepository(RedisRepository):
    @staticmethod
    def token_key(email: str) -> str:
        return f"coros:access_token:{email}"

    @staticmethod
    def latest_activity_key(email: str) -> str:
        return f"coros:latest_activity:{email}"

    def get_access_token(self, email: str) -> str | None:
        return self.get(self.token_key(email))

    def add_access_token(self, email: str, access_token: str) -> bool:
        return self.set(self.token_key(email), access_token, set_ex_time=True)

    def add_latest_activity_data(self, email: str, activity_data: dict) -> bool:
        return self.set(self.latest_activity_key(email), json.dumps(activity_data))

    def get_latest_activity_data(self, email: str) -> dict | None:
        data_key = self.latest_activity_key(email)

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
