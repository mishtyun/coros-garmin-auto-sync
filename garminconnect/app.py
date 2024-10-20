import os

import requests
from garth.exc import GarthHTTPError

from garminconnect import Garmin
from .configuration import garmin_connect_configuration
from garminconnect.exceptions import GarminConnectAuthenticationError


def get_mfa():
    """Get MFA."""
    return input("MFA one-time code: ")


def init_api():
    """Initialize Garmin API with your credentials."""

    try:
        print(
            f"Trying to login to Garmin Connect using token data from the tokenstore directory ...\n"
        )

        garmin = Garmin(garmin_connect_configuration)
        garmin.login()

    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
        print(
            "Login tokens not present, login with your Garmin Connect credentials to generate them.\n"
            f"They will be stored in tokenstore for future use.\n"
        )
        try:
            garmin = Garmin(
                garmin_connect_configuration,
                is_cn=False,
                prompt_mfa=get_mfa,
            )
            garmin.login()

            # Save Oauth1 and Oauth2 token files to directory for next login
            garmin.garth.dump(garmin_connect_configuration.tokenstore)

            print(
                f"Oauth tokens stored in tokenstore directory for future use. (first method)\n"
            )
            # Encode Oauth1 and Oauth2 tokens to base64 string and safe to file for next login (alternative way)
            token_base64 = garmin.garth.dumps()
            dir_path = os.path.expanduser(
                garmin_connect_configuration.tokenstore_base64
            )
            with open(dir_path, "w") as token_file:
                token_file.write(token_base64)
            print(
                f"Oauth tokens encoded as base64 string and saved to '{dir_path}' file for future use. (second method)\n"
            )
        except (
            FileNotFoundError,
            GarthHTTPError,
            GarminConnectAuthenticationError,
            requests.exceptions.HTTPError,
        ) as err:
            print(err)
            return None

    return garmin
