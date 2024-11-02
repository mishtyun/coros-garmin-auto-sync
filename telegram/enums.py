import enum


__all__ = ["DailyActivitiesDateTypes"]


class DailyActivitiesDateTypes(enum.Enum):
    choose_date = "choose_date"
    yesterday = "yesterday"
    today = "today"
