import asyncio
import logging
import time

from garmin_connect.configuration import GarminConnectConfiguration
from garmin_connect.exceptions import GarthHTTPError
from garmin_connect.service import Garmin

from garmin.oauth_repository import RedisOAuthRepository
from users.repository import get_user_redis_repository

__all__ = [
    "Garmin",
    "GarthHTTPError",
    "GarminMFARequiredError",
    "GarminSessionExpiredError",
    "login_with_credentials",
    "resume_client",
    "garmin_client_cache",
]

logger = logging.getLogger(__name__)


class GarminMFARequiredError(Exception):
    """Raised when the Garmin account requires MFA/2FA (not supported)."""


class GarminSessionExpiredError(Exception):
    """Raised when stored Garmin OAuth tokens are missing or no longer valid."""


def _raise_mfa_required(*args, **kwargs):
    raise GarminMFARequiredError("Garmin account requires MFA")


def _get_oauth_repository(tg_id: int) -> RedisOAuthRepository:
    return RedisOAuthRepository(
        tg_id=tg_id, user_repository=get_user_redis_repository()
    )


def login_with_credentials(tg_id: int, email: str, password: str) -> Garmin:
    """Log in to Garmin with email/password and persist OAuth tokens to Redis."""
    configuration = GarminConnectConfiguration(
        email=email, password=password, tokenstore="unused"
    )

    garmin = Garmin(
        _get_oauth_repository(tg_id), configuration, prompt_mfa=_raise_mfa_required
    )
    garmin.login(use_creds=True)
    garmin.garth.dumps()

    return garmin


def resume_client(tg_id: int, email: str) -> Garmin:
    """Build a Garmin client from OAuth tokens stored in Redis (no password)."""
    configuration = GarminConnectConfiguration(
        email=email, password="", tokenstore="unused"
    )

    garmin = Garmin(
        _get_oauth_repository(tg_id), configuration, prompt_mfa=_raise_mfa_required
    )

    try:
        garmin.login()
    except Exception as e:
        logger.info(f"Can't resume Garmin session for tg_id={tg_id}: {e}")
        raise GarminSessionExpiredError(
            f"Garmin session expired for tg_id={tg_id}"
        ) from e

    # persist OAuth2 token in case garth refreshed it during resume
    garmin.garth.dumps()

    return garmin


class GarminClientCache:
    def __init__(self, max_size: int = 16, idle_ttl: int = 60 * 30):
        self._max_size = max_size
        self._idle_ttl = idle_ttl
        self._clients: dict[int, tuple[Garmin, float]] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, tg_id: int, email: str) -> Garmin:
        async with self._lock:
            now = time.monotonic()

            if cached := self._clients.get(tg_id):
                client, last_used = cached
                if now - last_used < self._idle_ttl:
                    self._clients[tg_id] = (client, now)
                    return client
                del self._clients[tg_id]

            client = await asyncio.to_thread(resume_client, tg_id, email)

            self._evict_stale(now)
            self._clients[tg_id] = (client, now)
            return client

    def evict(self, tg_id: int) -> None:
        self._clients.pop(tg_id, None)

    def _evict_stale(self, now: float) -> None:
        self._clients = {
            tg_id: (client, last_used)
            for tg_id, (client, last_used) in self._clients.items()
            if now - last_used < self._idle_ttl
        }

        while len(self._clients) >= self._max_size:
            oldest_tg_id = min(self._clients, key=lambda k: self._clients[k][1])
            del self._clients[oldest_tg_id]


garmin_client_cache = GarminClientCache()
