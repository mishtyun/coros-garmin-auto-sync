import json
import logging

from core.repositories.redis_repository import RedisRepository, get_redis_client
from users.models import UserProfile

__all__ = ["UserRedisRepository", "get_user_redis_repository"]

logger = logging.getLogger(__name__)


class UserRedisRepository(RedisRepository):
    @staticmethod
    def profile_key(tg_id: int) -> str:
        return f"user:{tg_id}:profile"

    @staticmethod
    def garmin_oauth_key(tg_id: int) -> str:
        return f"user:{tg_id}:garmin_oauth"

    def get_profile(self, tg_id: int) -> UserProfile | None:
        profile_data = self.get(self.profile_key(tg_id))
        if not profile_data:
            return None

        try:
            return UserProfile.model_validate_json(profile_data)
        except ValueError:
            logger.warning(f"Can't parse profile data for tg_id={tg_id}")
            return None

    def save_profile(self, profile: UserProfile) -> bool:
        return self.set(self.profile_key(profile.tg_id), profile.model_dump_json())

    def get_all_profiles(self) -> list[UserProfile]:
        profiles = []
        for key in self.redis.scan_iter(match="user:*:profile"):
            profile_data = self.get(key.decode() if isinstance(key, bytes) else key)
            if not profile_data:
                continue
            try:
                profiles.append(UserProfile.model_validate_json(profile_data))
            except ValueError:
                logger.warning(f"Can't parse profile data for key={key}")
        return profiles

    def get_garmin_oauth(self, tg_id: int) -> dict | None:
        oauth_data = self.get(self.garmin_oauth_key(tg_id))
        if not oauth_data:
            return None

        try:
            return json.loads(oauth_data)
        except json.JSONDecodeError:
            logger.warning(f"Can't parse garmin oauth data for tg_id={tg_id}")
            return None

    def set_garmin_oauth(self, tg_id: int, oauth_data: dict) -> bool:
        return self.set(
            self.garmin_oauth_key(tg_id), json.dumps(oauth_data, default=str)
        )

    def delete_user(self, tg_id: int) -> None:
        from coros.repositories.redis_repository import CorosRedisRepository

        keys_to_delete = [self.profile_key(tg_id), self.garmin_oauth_key(tg_id)]

        if profile := self.get_profile(tg_id):
            keys_to_delete += [
                CorosRedisRepository.token_key(profile.coros_email),
                CorosRedisRepository.latest_activity_key(profile.coros_email),
            ]

        self.redis.delete(*keys_to_delete)


def get_user_redis_repository(**kwargs) -> UserRedisRepository:
    return UserRedisRepository(redis=get_redis_client(), **kwargs)
