from dataclasses import dataclass

from coros.configuration import CorosConfiguration
from garmin.client import Garmin, garmin_client_cache
from users.models import UserProfile

__all__ = ["UserContext"]


@dataclass
class UserContext:
    tg_id: int
    profile: UserProfile

    @property
    def coros_config(self) -> CorosConfiguration:
        return CorosConfiguration(
            email=self.profile.coros_email,
            password_md5=self.profile.coros_password_md5,
        )

    async def get_garmin(self) -> Garmin:
        return await garmin_client_cache.get_or_create(
            self.tg_id, self.profile.garmin_email
        )
