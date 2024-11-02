from asyncio import sleep

from garmin_connect.service import Garmin

from coros.configuration import coros_configuration
from coros.models import DateActivityFilter
from coros.services import AuthService
from coros.services.activity import ActivityService


__all__ = [
    "get_activity_url",
    "upload_and_get_url",
    "sync_all_activity_by_dates_handler",
]


def get_activity_url(activity_id: str):
    return f"https://connect.garmin.com/modern/activity/{activity_id}"


async def upload_and_get_url(garmin_api: Garmin, file_path: str) -> str | None:
    try:
        garmin_api.upload_activity(file_path)

        await sleep(3)

        latest_activity = garmin_api.get_last_activity()
        activity_id = latest_activity.get("activityId")

        garmin_api.change_activity_visibility(activity_id, "public")
        return get_activity_url(activity_id)
    except Exception as e:
        print(e)


async def sync_all_activity_by_dates_handler(
    garmin_api: Garmin, start_date: str, end_date: str
) -> str:

    AuthService(coros_configuration).get_access_token()
    file_paths = ActivityService(coros_configuration).download_daily_activities(
        DateActivityFilter(start_date=start_date, end_date=end_date)
    )

    activity_links = []

    for file_path in file_paths:
        garmin_activity_link = await upload_and_get_url(garmin_api, file_path)
        if not garmin_activity_link:
            continue
        activity_links.append(garmin_activity_link)

    return (
        "\n".join(activity_links)
        if activity_links
        else "No activities or already synced"
    )
