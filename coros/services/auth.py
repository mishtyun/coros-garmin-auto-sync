import urllib3


from coros.services.base import BaseService

__all__ = ["AuthService"]


class AuthService(BaseService):
    @property
    def login_url(self):
        return self.configuration.api_url + "/account/login"

    def login(self) -> dict:
        body = {
            "account": self.configuration.email,
            "accountType": 2,
            "pwd": self.configuration.hashed_password,
        }

        res = urllib3.request(
            "POST",
            self.login_url,
            json=body,
            headers={
                "content-type": "application/json",
            },
        )
        return res.json()

    def get_access_token(self):
        if access_token := self.redis_repository.get(self.configuration.email):
            return access_token

        login_response = self.login()
        access_token = login_response.get("data", {}).get("accessToken")
        if not access_token:
            ...

        self.redis_repository.add_access_token(self.configuration.email, access_token)
        return access_token
