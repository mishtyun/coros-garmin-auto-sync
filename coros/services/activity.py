import urllib3

from coros.services import BaseService
from coros.services.utils import get_caller_name


class ActivityService(BaseService):

    API_URLS = {"get_activities": "/activity/query?size=10&pageNumber=1&modeList="}

    @property
    def url(self):
        return self.configuration.api_url + self.API_URLS.get(get_caller_name())

    def get_headers(self) -> dict:
        headers = super().get_headers()
        headers.update(
            {
                "accesstoken": self.redis_repository.get(self.configuration.email),
            }
        )
        return headers

    def get_activities(self):
        url = self.url
        headers = self.get_headers()

        res = urllib3.request("GET", url, headers=headers)
        return res.json()
