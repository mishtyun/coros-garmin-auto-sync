from enum import Enum

__all__ = ["ActivityFileType", "API_URLS"]


class ActivityFileType(Enum):
    FIT = 4
    TCX = 3
    CSV = 0


API_URLS = {
    "get_activities": "/activity/query?size={size}&pageNumber={page_number}",
    "get_latest_activity": "/activity/query?size=1&pageNumber=1",
    "download_latest_activity": "/activity/detail/download?labelId={label_id}&sportType={sport_type}&fileType={file_type}",
}
