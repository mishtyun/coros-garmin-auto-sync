from garmin_connect.app import init_api
from garmin_connect.configuration import GarminConnectConfiguration
from garmin_connect.service import Garmin

from core.redis import get_redis_client_with_default_config
from garmin.repository import RedisOAuthRepository


def get_garmin_api() -> Garmin:
    garmin_connect_config = GarminConnectConfiguration()
    oauth_repo = RedisOAuthRepository(get_redis_client_with_default_config())

    garmin_api = init_api(
        oauth_repo=oauth_repo, garmin_connect_configuration=garmin_connect_config
    )
    return garmin_api
