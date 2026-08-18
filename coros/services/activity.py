import io
import logging
import os
import shutil
from typing import Sequence

from pydantic import TypeAdapter
from urllib3 import HTTPResponse

from core.configuration import STATIC_ROOT
from coros.constants import API_URLS, ActivityFileType
from coros.models import ActivityShortSchema, DateActivityFilter
from coros.services import BaseService
from coros.services.utils import get_caller_name, get_file_name

logger = logging.getLogger(__name__)


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
            logger.warning(f"Can not get url for {caller_url}")

        url = self.configuration.api_url + caller_url

        if date_filters:
            url += f"&startDay={date_filters.start_date}&endDay={date_filters.end_date}"

        return url

    def get_headers(self) -> dict:
        headers = super().get_headers()
        headers.update(
            {
                "accesstoken": self.redis_repository.get_access_token(
                    self.configuration.email
                ),
            }
        )
        return headers

    def get_activities(
        self, date_filters: DateActivityFilter | None = None
    ) -> list[ActivityShortSchema]:
        activities_url = self.get_url(date_filters=date_filters)
        res = self.http.request("GET", activities_url, headers=self.get_headers())

        activities_data = res.json().get("data", {}).get("dataList")
        if not activities_data or not isinstance(activities_data, Sequence):
            return []

        ta = TypeAdapter(list[ActivityShortSchema])
        return ta.validate_python(activities_data)

    def get_latest_activity(
        self,
        *,
        date_filters: DateActivityFilter | None = None,
        save_response: bool = False,
    ) -> None | ActivityShortSchema:
        latest_activity_url = self.get_url(date_filters=date_filters, size=1)
        res = self.http.request("GET", latest_activity_url, headers=self.get_headers())

        activity_data = res.json().get("data", {}).get("dataList")
        if not activity_data or not isinstance(activity_data, Sequence):
            return None

        activity_data = activity_data[0]
        activity_model = ActivityShortSchema.model_validate(activity_data)

        if save_response:
            self.redis_repository.add_latest_activity_data(
                self.configuration.email, activity_model.model_dump()
            )

        return activity_model

    @staticmethod
    def _get_activity_file_path(
        activity_model: ActivityShortSchema,
        extension: str = ActivityFileType.FIT.name,
        return_only_name: bool = False,
    ) -> str:
        file_name = get_file_name(
            base_name=activity_model.name,
            extension=extension.lower(),
            label_id=activity_model.label_id,
            sport_type=activity_model.sport_type,
        )

        if return_only_name:
            return file_name

        return os.path.join(STATIC_ROOT, file_name)

    @staticmethod
    def _validate_response(response: HTTPResponse) -> dict:
        if response.status != 200:
            logger.info(response.reason)
            return {}
        return response.json()

    def download_activity(self, activity: ActivityShortSchema) -> str | None:
        file_path = self._get_activity_file_path(activity)

        if os.path.exists(file_path):
            logger.info(
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
            logger.info(f"Issue with {activity_file_url=}, for {activity.label_id=}")
            return None

        with self.http.request(
            "GET", activity_file_url, preload_content=False
        ) as resp, open(file_path, "wb") as out_file:
            shutil.copyfileobj(resp, out_file)

        return file_path

    def get_activity_bytes(
        self, activity: ActivityShortSchema
    ) -> tuple[str, io.BytesIO] | None:
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
            logger.info(f"Issue with {activity_file_url=}, for {activity.label_id=}")
            return None, None

        with self.http.request("GET", activity_file_url, preload_content=False) as resp:
            file_content = resp.read()

        file_name = self._get_activity_file_path(activity, return_only_name=True)

        return file_name, io.BytesIO(file_content)

    def download_daily_activities(
        self, date_filters: DateActivityFilter | None = None
    ) -> list[str]:
        activities_to_download = self.get_activities(date_filters=date_filters)

        file_paths = []
        for activity in activities_to_download:
            file_path = self.download_activity(activity)
            if not file_path:
                logger.info(
                    f"Can not download activity for {activity.label_id=}, {activity.name=}"
                )
                continue
            file_paths.append(file_path)

        return file_paths

    def get_daily_activities_bytes(
        self, date_filters: DateActivityFilter | None = None
    ) -> list[tuple[str, io.BytesIO]]:
        activities_to_download = self.get_activities(date_filters=date_filters)

        files = []
        for activity in activities_to_download:
            activity_name, activity_content = self.get_activity_bytes(activity)
            if not activity_name or not activity_content:
                logger.info(
                    f"Can not download activity for {activity.label_id=}, {activity.name=}"
                )
                continue
            files.append((activity_name, activity_content))

        return files

    def download_latest_activity(self) -> str:
        latest_activity: ActivityShortSchema | None = self.get_latest_activity(
            save_response=False
        )
        return self.download_activity(latest_activity)

    def get_latest_activity_bytes(self) -> tuple[str, io.BytesIO] | tuple[None, None]:
        latest_activity: ActivityShortSchema | None = self.get_latest_activity(
            save_response=False
        )

        if not latest_activity:
            logger.info("[get_latest_activity_bytes] Last activity not found")
            return None, None

        activity_name, activity_content = self.get_activity_bytes(latest_activity)

        return activity_name, activity_content
