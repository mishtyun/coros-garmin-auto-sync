from typing import Tuple

from garmin_connect.repository import BaseOAuthRepository
from garth.auth_tokens import OAuth1Token, OAuth2Token
from garth.utils import asdict
from redis import Redis


class RedisOAuthRepository(BaseOAuthRepository):
    OAUTH1_KEY = "garmin_connect_oauth1_token"
    OAUTH2_KEY = "garmin_connect_oauth1_token"

    def __init__(self, redis: Redis):
        self.redis = redis

    def get_oauth(self) -> Tuple[OAuth1Token, OAuth2Token]:
        oauth1_token_value = self.redis.get(self.OAUTH1_KEY)
        if not oauth1_token_value:
            ...
        oauth1_token: dict = oauth1_token_value.decode()

        oauth2_token_value = self.redis.get(self.OAUTH1_KEY)
        if not oauth2_token_value:
            ...
        oauth2_token: dict = oauth2_token_value.decode()

        return OAuth1Token(**oauth1_token), OAuth2Token(**oauth2_token)

    def set_oauth(self, oauth1_token: OAuth1Token, oauth2_token: OAuth2Token) -> bool:
        self.redis.set(self.OAUTH1_KEY, asdict(oauth1_token))
        self.redis.set(self.OAUTH2_KEY, asdict(oauth1_token))
        return True
