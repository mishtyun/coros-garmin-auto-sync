import json

import urllib3

from coros.configuration import CorosConfiguration

configuration = CorosConfiguration()


login_url = configuration.api_url + "/account/login"

login_body = {
    "account": configuration.email,
    "accountType": 2,
    "pwd": configuration.hashed_password,
}

res = urllib3.request("POST", login_url, body=json.dumps(login_body))
login_response = res.json()

access_token = login_response.get("data").get("accessToken")


# save this token, and then just use it in headers to get smth from the API's
