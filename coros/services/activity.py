import urllib3

from coros.constants import ActivityFileType
from coros.models.activity import Activity
from coros.services import BaseService
from coros.services.utils import get_caller_name


class ActivityService(BaseService):
    DEFAULT_PAGE_SIZE = 10
    DEFAULT_PAGE_NUMBER = 1

    API_URLS = {
        "get_activities": "/activity/query?size={size}&pageNumber={page_number}",
        "get_latest_activity": "/activity/query?size=1&pageNumber=1",
        "download_latest_activity": "/activity/detail/download",
    }

    def get_url(self, **query_params):
        if "size" not in query_params:
            query_params["size"] = self.DEFAULT_PAGE_SIZE
        if "page_number" not in query_params:
            query_params["page_number"] = self.DEFAULT_PAGE_NUMBER

        return self.configuration.api_url + self.API_URLS.get(
            get_caller_name(), ""
        ).format(**query_params)

    def get_headers(self) -> dict:
        headers = super().get_headers()
        headers.update(
            {
                "accesstoken": self.redis_repository.get(self.configuration.email),
            }
        )
        return headers

    def get_activities(self):
        res = urllib3.request("GET", self.get_url(), headers=self.get_headers())
        return res.json()

    def get_latest_activity(self, save_response: bool = False) -> None | Activity:
        res = urllib3.request("GET", self.get_url(size=1), headers=self.get_headers())

        activity_data = res.json().get("data", {}).get("dataList")
        if not activity_data or not isinstance(activity_data, list):
            return None

        activity_data = activity_data[0]
        activity_model = Activity.model_validate(activity_data)

        if save_response:
            self.redis_repository.get_latest_activity_data(activity_model.model_dump())

        return activity_model

    def download_latest_activity(self):
        latest_activity: Activity = self.get_latest_activity(save_response=False)

        query_params_to_download = {
            "labelId": latest_activity.label_id,
            "sportType": latest_activity.sport_type,
            "fileType": ActivityFileType.FIT,
        }

        downloaded_file = urllib3.request(
            method="GET",
            headers=self.get_headers(),
            url=self.get_url(**query_params_to_download),
        )
        return downloaded_file
