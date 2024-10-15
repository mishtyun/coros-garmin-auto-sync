from coros.configuration import coros_configuration
from coros.services import AuthService
from coros.services.activity import ActivityService


if __name__ == "__main__":
    from coros.models.filters import DateActivityFilter

    auth_service = AuthService(coros_configuration)
    access_token = auth_service.get_access_token()

    a = ActivityService(coros_configuration).get_activities(
        DateActivityFilter(start_date="20241003", end_date="20241003")
    )
    latest_activity = ActivityService(coros_configuration).download_latest_activity()
