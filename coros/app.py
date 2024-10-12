from coros.configuration import CorosConfiguration, RedisConfiguration
from coros.services import AuthService
from coros.services.activity import ActivityService

redis_configuration = RedisConfiguration()
coros_configuration = CorosConfiguration()


if __name__ == "__main__":
    auth_service = AuthService(coros_configuration)
    access_token = auth_service.get_access_token()
    activities = ActivityService(coros_configuration).get_activities()
