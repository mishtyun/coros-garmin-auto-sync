import logging

import urllib3

from coros.repositories.redis_repository import get_coros_redis_repository
from coros.configuration import CorosConfiguration

__all__ = ["BaseService", "CorosReloginError", "TOKEN_INVALID_RESULT"]

logger = logging.getLogger(__name__)

TOKEN_INVALID_RESULT = "1019"


class CorosReloginError(Exception):
    pass


class BaseService(object):
    def __init__(self, configuration: CorosConfiguration):
        self.configuration = configuration
        self.redis_repository = get_coros_redis_repository(
            expired_time=self.configuration.access_token_expired_time
        )

        self.http = urllib3.PoolManager()

    def get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
        }

    def refresh_access_token(self) -> None:
        # Deferred import: AuthService subclasses BaseService.
        from coros.services.auth import AuthService

        access_token = AuthService(self.configuration).send_login_request(
            return_token=True
        )
        if not access_token or not isinstance(access_token, str):
            raise CorosReloginError("Coros re-login failed")
        self.redis_repository.add_access_token(self.configuration.email, access_token)

    def request_json(
        self,
        method: str,
        url: str,
        *,
        payload: dict | None = None,
        retry: bool = True,
    ) -> dict:
        """Authenticated Coros API call returning the parsed JSON body.

        Coros can invalidate a cached access token before our Redis TTL
        expires (e.g. a Training Hub web login issues a new token) — on
        result=1019 we re-login and retry once. Non-200 responses are
        logged and returned as an empty dict.
        """
        kwargs: dict = {"headers": self.get_headers()}
        if payload is not None:
            kwargs["json"] = payload

        response = self.http.request(method, url, **kwargs)
        if response.status != 200:
            logger.info(f"Coros returned HTTP {response.status} for {url}")
            return {}

        body: dict = response.json()
        if body.get("result") == TOKEN_INVALID_RESULT and retry:
            logger.info("Coros access token invalid, re-authenticating")
            self.refresh_access_token()
            return self.request_json(method, url, payload=payload, retry=False)
        return body
