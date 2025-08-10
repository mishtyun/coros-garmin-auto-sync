import urllib3

from core.repositories.redis_repository import get_redis_repository
from coros.configuration import CorosConfiguration

__all__ = ["BaseService"]


class BaseService(object):
    def __init__(self, configuration: CorosConfiguration):
        self.configuration = configuration
        self.redis_repository = get_redis_repository(
            expired_time=self.configuration.access_token_expired_time
        )

        self.http = urllib3.PoolManager()

    def get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
        }
