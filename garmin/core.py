from garmin_connect.app import init_api
from garmin_connect.configuration import GarminConnectConfiguration
from garmin_connect.repository import FileOAuthRepository
from garmin_connect.service import Garmin


def get_garmin_api() -> Garmin:
    garmin_connect_config = GarminConnectConfiguration()
    oauth_repo = FileOAuthRepository(garmin_connect_config.tokenstore)

    garmin_api = init_api(
        oauth_repo=oauth_repo, garmin_connect_configuration=garmin_connect_config
    )
    return garmin_api
