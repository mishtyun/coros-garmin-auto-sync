import enum


__all__ = ["DailyActivitiesTypes"]


class DailyActivitiesTypes(enum.Enum):
    choose_date = "choose_date"
    yesterday = "yesterday"
    today = "today"
