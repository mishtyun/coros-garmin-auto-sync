from garmin_connect.app import init_api
from garmin_connect.configuration import garmin_connect_configuration
from garmin_connect.repository import FileOAuthRepository

__all__ = ["garmin_api"]

garmin_api = init_api(
    oauth_repo=FileOAuthRepository(garmin_connect_configuration.tokenstore),
    garmin_connect_configuration=garmin_connect_configuration,
)
