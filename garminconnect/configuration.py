from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["garmin_connect_configuration", "GarminConnectConfiguration"]


class GarminConnectConfiguration(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="garmin_connect_", env_file="../.env", extra="allow"
    )

    email: str
    password: str
    tokenstore: str = Field(default="~/.garminconnect")


garmin_connect_configuration = GarminConnectConfiguration()
