from coros.configuration import CorosConfiguration
from coros.services import AuthService
from coros.services.activity import ActivityService

configuration = CorosConfiguration()

access_token = AuthService(configuration).get_access_token()
# configuration.access_token = "UKWL853IX85OF1LFR4Q2PK8FIYEI3SPN"
ActivityService(configuration).get_activities()

# save this token, and then just use it in headers to get smth from the API's
