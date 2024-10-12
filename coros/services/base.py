from coros.repositories.redis_repository import get_redis_repository
from coros.configuration import CorosConfiguration

__all__ = ["BaseService"]


class BaseService(object):
    def __init__(self, configuration: CorosConfiguration):
        self.configuration = configuration
        self.redis_repository = get_redis_repository()

    def get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
        }
