import logging

from coros.services.base import BaseService

logger = logging.getLogger(__name__)

__all__ = ["AuthService", "CorosAuthError"]


class CorosAuthError(Exception):
    """Raised when a Coros access token can't be obtained."""


class AuthService(BaseService):
    @property
    def login_url(self):
        return self.configuration.api_url + "/account/login"

    def send_login_request(self, return_token: bool = False) -> dict | str | None:
        body = {
            "account": self.configuration.email,
            "accountType": 2,
            "pwd": self.configuration.hashed_password,
        }

        res = self.http.request(
            "POST",
            self.login_url,
            json=body,
            headers={"content-type": "application/json"},
        )

        res_body: dict = res.json()

        if return_token:
            return res_body.get("data", {}).get("accessToken")

        return res_body

    def get_or_set_access_token(self) -> str | None:
        if access_token := self.redis_repository.get_access_token(
            self.configuration.email
        ):
            logger.debug("[get_or_set_access_token] Return access_token from redis")
            return access_token

        access_token = self.send_login_request(return_token=True)
        if not access_token:
            logger.warning("[get_or_set_access_token] Failed to get access_token")
            return None

        self.redis_repository.add_access_token(self.configuration.email, access_token)
        return access_token
