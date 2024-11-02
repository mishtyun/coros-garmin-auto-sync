import os
import shutil
from typing import Sequence

from pydantic import TypeAdapter
from urllib3 import HTTPResponse

from coros.configuration import STATIC_ROOT
from coros.constants import ActivityFileType, API_URLS
from coros.models import Activity, DateActivityFilter
from coros.services import BaseService
from coros.services.utils import get_caller_name, get_file_name


class ActivityService(BaseService):
    DEFAULT_PAGE_SIZE = 10
    DEFAULT_PAGE_NUMBER = 1

    def get_url(
        self, *, date_filters: DateActivityFilter | None = None, **query_params
    ):
        if "size" not in query_params:
            query_params["size"] = self.DEFAULT_PAGE_SIZE
        if "page_number" not in query_params:
            query_params["page_number"] = self.DEFAULT_PAGE_NUMBER

        caller_name = get_caller_name()
        caller_url = API_URLS.get(caller_name, "").format(**query_params)

        if not caller_url:
            print(f"Can not get url for {caller_url}")

        url = self.configuration.api_url + caller_url

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

    def get_activities(
        self, date_filters: DateActivityFilter | None = None
    ) -> list[Activity]:
        activities_url = self.get_url(date_filters=date_filters)
        res = self.http.request("GET", activities_url, headers=self.get_headers())

        activities_data = res.json().get("data", {}).get("dataList")
        if not activities_data or not isinstance(activities_data, Sequence):
            return []

        ta = TypeAdapter(list[Activity])
        return ta.validate_python(activities_data)

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
            self.redis_repository.add_latest_activity_data(activity_model.model_dump())

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

    @staticmethod
    def _validate_response(response: HTTPResponse) -> dict:
        if response.status != 200:
            print(response.reason)
            return {}
        return response.json()

    def download_activity(self, activity: Activity) -> str | None:
        file_path = self._get_activity_file_path(activity)

        if os.path.exists(file_path):
            print(
                f"Activity file already exists for {activity.name}, {activity.label_id}"
            )
            return file_path

        query_params_to_download = {
            "label_id": activity.label_id,
            "sport_type": activity.sport_type,
            "file_type": ActivityFileType.FIT.value,
        }

        file_to_download_response = self.http.request(
            method="GET",
            headers=self.get_headers(),
            url=self.get_url(**query_params_to_download),
        )

        file_to_download_data = self._validate_response(file_to_download_response)
        activity_file_url = file_to_download_data.get("data", {}).get("fileUrl")

        if not activity_file_url:
            print(f"Issue with {activity_file_url=}, for {activity.label_id=}")
            return None

        with self.http.request(
            "GET", activity_file_url, preload_content=False
        ) as resp, open(file_path, "wb") as out_file:
            shutil.copyfileobj(resp, out_file)

        return file_path

    def download_daily_activities(
        self, date_filters: DateActivityFilter | None = None
    ) -> list[str]:
        activities_to_download = self.get_activities(date_filters=date_filters)

        file_paths = []
        for activity in activities_to_download:
            file_path = self.download_activity(activity)
            if not file_path:
                print(
                    f"Can not download activity for {activity.label_id=}, {activity.name=}"
                )
                continue
            file_paths.append(file_path)

        return file_paths

    def download_latest_activity(self) -> str:
        latest_activity: Activity = self.get_latest_activity(save_response=False)
        return self.download_activity(latest_activity)
