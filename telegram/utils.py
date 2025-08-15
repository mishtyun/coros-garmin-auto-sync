import logging
from asyncio import sleep
from typing import IO, NewType

from garmin_connect.exceptions import GarthHTTPError
from garmin_connect.service import Garmin

from coros.configuration import coros_configuration
from coros.models import Activity, DateActivityFilter
from coros.services import AuthService
from coros.services.activity import ActivityService

logger = logging.getLogger(__name__)


__all__ = [
    "get_activity_url",
    "upload_and_get_url",
    "get_activities_message",
    "sync_all_activity_by_dates_handler",
]

Activities = NewType("Activities", list[Activity])


def get_activity_url(activity_id: str):
    return f"https://connect.garmin.com/modern/activity/{activity_id}"


async def upload_and_get_url(
    garmin_api: Garmin, file_name: str, file: IO[bytes]
) -> tuple[bool, str] | tuple[bool, None]:
    try:
        garmin_api.upload_activity_from_binary(file_name, file)
        uploaded = True
        await sleep(3)
    except GarthHTTPError as e:
        error_json: dict = e.error.response.json()
        error_messages = (
            error_json.get("detailedImportResult").get("failures")[0].get("messages")
        )

        duplicate_message = {"code": 202, "content": "Duplicate Activity."}

        if duplicate_message not in error_messages:
            raise Exception from e

        uploaded = False
        logger.info("Activity already exists. Skipping upload.")

    except Exception as e:
        logger.error(e)
        return False, None

    latest_activity = garmin_api.get_last_activity()
    activity_id = latest_activity.get("activityId")

    garmin_api.change_activity_visibility(activity_id, "public")
    return uploaded, get_activity_url(activity_id)


async def sync_all_activity_by_dates_handler(
    garmin_api: Garmin, start_date: str, end_date: str
) -> list[str]:
    """
    Sync (download from Coros and upload into Garmin) available activities between specific dates
    :param garmin_api: Garmin-Api instance
    :param start_date: String in the format YYYYMMDD
    :param end_date: String in the format YYYYMMDD
    :return: list of activity links
    """

    AuthService(coros_configuration).get_or_set_access_token()
    # file_paths = ActivityService(coros_configuration).download_daily_activities(
    #     DateActivityFilter(start_date=start_date, end_date=end_date)
    # )
    files = ActivityService(coros_configuration).get_daily_activities_bytes(
        DateActivityFilter(start_date=start_date, end_date=end_date)
    )

    activity_links = []

    # for file_path in file_paths:
    #     garmin_activity_link = await upload_and_get_url(garmin_api, file_path)
    #     if not garmin_activity_link:
    #         activity_links.append("One of the activity was synced already :)")
    #         continue
    #     activity_links.append(garmin_activity_link)

    for file_name, file_content in files:
        _, garmin_activity_link = await upload_and_get_url(
            garmin_api, file_name=file_name, file=file_content
        )
        if not garmin_activity_link:
            activity_links.append("One of the activity was synced already :)")
            continue
        activity_links.append(garmin_activity_link)

    return activity_links


def get_activities_message(activities: Activities) -> str:
    message_to_send = ""
    for activity in activities:
        activity_url = get_activity_url(activity["activityId"])
        message_to_send += f"{activity['activityName']}: {activity_url}\n"

    return message_to_send if message_to_send else "No activities"
