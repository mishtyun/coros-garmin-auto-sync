import inspect
from pathlib import Path

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
                "accesstoken": self.configuration.access_token,
                # "accesstoken": "6IA8NY3IX8OQK09KHS9ERLFDPX1A53J9",
                # "csrfToken": "7-lYGApKlRhfBOdVzV_lEylo",
                # "CPL-coros-token": "5LS77H3IX8M4YIHEYOEHYKET98EWOLAP",
                # "openId": "e7970f4f922b4f8088270c655a4d99c3",
                # "rg": "rg3",
                # "CPL-coros-region": 3,
                # "Cookie": "_ga=GA1.1.499996448.1728143194; CPL-coros-region=3; rg=rg3; openId=e7970f4f922b4f8088270c655a4d99c3; access_token=rg3-cfdf32659e4bc635f991ba961aba3bda; _ga_P18WV8BE1H=GS1.1.1728722924.5.0.1728722924.60.0.0; CPL-coros-token=6IA8NY3IX8OQK09KHS9ERLFDPX1A53J9",
            }
        )
        return headers

    def get_activities(self):
        url = self.url
        headers = self.get_headers()

        res = urllib3.request("GET", url, headers=headers)
        print(res.json())
        return res.json()
