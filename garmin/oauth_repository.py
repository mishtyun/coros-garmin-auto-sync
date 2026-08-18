from typing import Tuple

from garmin_connect.repository import BaseOAuthRepository
from garth.auth_tokens import OAuth1Token, OAuth2Token
from garth.utils import asdict

from users.repository import UserRedisRepository

__all__ = ["GarminOAuthNotFoundError", "RedisOAuthRepository"]


class GarminOAuthNotFoundError(FileNotFoundError):
    """Raised when no stored Garmin OAuth tokens exist for a user.

    Subclasses FileNotFoundError so Garmin.login() token-resume error
    handling treats it like a missing tokenstore.
    """


class RedisOAuthRepository(BaseOAuthRepository):
    def __init__(self, tg_id: int, user_repository: UserRedisRepository):
        self.tg_id = tg_id
        self.user_repository = user_repository

    def get_oauth(self) -> Tuple[OAuth1Token, OAuth2Token]:
        oauth_data = self.user_repository.get_garmin_oauth(self.tg_id)
        if not oauth_data:
            raise GarminOAuthNotFoundError(
                f"No Garmin OAuth tokens for tg_id={self.tg_id}"
            )

        return (
            OAuth1Token(**oauth_data["oauth1"]),
            OAuth2Token(**oauth_data["oauth2"]),
        )

    def set_oauth(self, oauth1_token: OAuth1Token, oauth2_token: OAuth2Token) -> bool:
        return self.user_repository.set_garmin_oauth(
            self.tg_id,
            {"oauth1": asdict(oauth1_token), "oauth2": asdict(oauth2_token)},
        )
