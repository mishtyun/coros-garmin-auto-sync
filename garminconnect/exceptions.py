__all__ = [
    "GarminConnectConnectionError",
    "GarminConnectTooManyRequestsError",
    "GarminConnectAuthenticationError",
    "GarminConnectInvalidFileFormatError",
]


class GarminConnectConnectionError(Exception):
    """Raised when communication ended in error."""


class GarminConnectTooManyRequestsError(Exception):
    """Raised when rate limit is exceeded."""


class GarminConnectAuthenticationError(Exception):
    """Raised when authentication is failed."""


class GarminConnectInvalidFileFormatError(Exception):
    """Raised when an invalid file format is passed to upload."""
