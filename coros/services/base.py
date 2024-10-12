from coros.configuration import CorosConfiguration


__all__ = ["BaseService"]


class BaseService(object):
    def __init__(self, configuration: CorosConfiguration):
        self.configuration = configuration

    def get_headers(self) -> dict:
        return {
            # "Content-Type": "application/json",
        }
