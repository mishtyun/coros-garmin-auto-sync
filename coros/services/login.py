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
        if self.configuration.access_token:
            return self.configuration.access_token

        login_response = self.login()
        access_token = login_response.get("data", {}).get("accessToken")
        if not access_token:
            ...

        self.configuration.access_token = access_token
        return self.configuration.access_token


# rg3 - cfdf32659e4bc635f991ba961aba3bda
# rg3 - 50DTNW3IX8LULKE6F44VC851OLB5LMGQ
# 5LS77H3IX8M4YIHEYOEHYKET98EWOLAP
