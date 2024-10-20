import os
import shutil
from typing import Sequence

from coros.configuration import STATIC_ROOT
from coros.constants import ActivityFileType
from coros.models import Activity, DateActivityFilter, activity
from coros.services import BaseService
from coros.services.utils import get_caller_name, get_file_name


class ActivityService(BaseService):
    DEFAULT_PAGE_SIZE = 10
    DEFAULT_PAGE_NUMBER = 1

    API_URLS = {
        "get_activities": "/activity/query?size={size}&pageNumber={page_number}",
        "get_latest_activity": "/activity/query?size=1&pageNumber=1",
        "download_latest_activity": "/activity/detail/download?labelId={label_id}&sportType={sport_type}&fileType={file_type}",
    }

    def get_url(
        self, *, date_filters: DateActivityFilter | None = None, **query_params
    ):
        if "size" not in query_params:
            query_params["size"] = self.DEFAULT_PAGE_SIZE
        if "page_number" not in query_params:
            query_params["page_number"] = self.DEFAULT_PAGE_NUMBER

        url = self.configuration.api_url + self.API_URLS.get(
            get_caller_name(), ""
        ).format(**query_params)

        if date_filters:
            url += f"&startDay={date_filters.start_date}&endDay={date_filters.end_date}"

        return url

    def get_headers(self) -> dict:
        headers = super().get_headers()
        headers.update(
            {
                "accesstoken": self.redis_repository.get(self.configuration.email),
            }
        )
        return headers

    def get_activities(self, date_filters: DateActivityFilter | None = None):
        activities_url = self.get_url(date_filters=date_filters)
        res = self.http.request("GET", activities_url, headers=self.get_headers())
        return res.json()

    def get_latest_activity(
        self,
        *,
        date_filters: DateActivityFilter | None = None,
        save_response: bool = False,
    ) -> None | Activity:
        latest_activity_url = self.get_url(date_filters=date_filters, size=1)
        res = self.http.request("GET", latest_activity_url, headers=self.get_headers())

        activity_data = res.json().get("data", {}).get("dataList")
        if not activity_data or not isinstance(activity_data, Sequence):
            return None

        activity_data = activity_data[0]
        activity_model = Activity.model_validate(activity_data)

        if save_response:
            self.redis_repository.get_latest_activity_data(activity_model.model_dump())

        return activity_model

    @staticmethod
    def _get_activity_file_path(
        activity_model: Activity,
        extension: str = ActivityFileType.FIT.name,
    ) -> str:
        filename = get_file_name(
            base_name=activity_model.name,
            extension=extension.lower(),
            label_id=activity_model.label_id,
            sport_type=activity_model.sport_type,
        )
        return os.path.join(STATIC_ROOT, filename)

    def download_latest_activity(self):
        latest_activity: Activity = self.get_latest_activity(save_response=False)
        file_path = self._get_activity_file_path(latest_activity)

        if os.path.exists(file_path):
            print(
                f"Activity file already exists for {latest_activity.name}, {latest_activity.label_id}"
            )
            return file_path

        query_params_to_download = {
            "label_id": latest_activity.label_id,
            "sport_type": latest_activity.sport_type,
            "file_type": ActivityFileType.FIT.value,
        }

        file_to_download_response = self.http.request(
            method="GET",
            headers=self.get_headers(),
            url=self.get_url(**query_params_to_download),
        )

        # TODO validate response from coros-api service
        file_to_download_data = file_to_download_response.json()
        activity_file_url = file_to_download_data.get("data", {}).get("fileUrl")

        with self.http.request(
            "GET", activity_file_url, preload_content=False
        ) as resp, open(file_path, "wb") as out_file:
            shutil.copyfileobj(resp, out_file)

        return file_path
