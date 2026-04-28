import time
from typing import Callable, Mapping, Optional, Protocol

DEFAULT_RETRY_AFTER_SECONDS = 60


class BrowseResponse(Protocol):
    """Small response protocol used by the browse retry helper."""

    status_code: int
    headers: Mapping[str, str]

    def json(self) -> dict[str, object]:
        """Return a decoded JSON response body."""

    def raise_for_status(self) -> None:
        """Raise an HTTP error if the response is unsuccessful."""


class BrowseSession(Protocol):
    """Small session protocol used by the browse retry helper."""

    def get(
        self,
        url: str,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> BrowseResponse:
        """Issue a GET request."""


Sleeper = Callable[[float], None]


def parse_retry_after(
    headers: Mapping[str, str],
    default_seconds: int = DEFAULT_RETRY_AFTER_SECONDS,
) -> int:
    """Parse Retry-After seconds, falling back to a conservative default."""
    try:
        return int(headers.get("Retry-After", default_seconds))
    except (TypeError, ValueError):
        return default_seconds


def get_with_rate_limit_retry(
    session: BrowseSession,
    url: str,
    headers: Mapping[str, str],
    params: Mapping[str, object],
    *,
    max_retries: int = 1,
    sleeper: Optional[Sleeper] = None,
) -> BrowseResponse:
    """GET a Browse API URL and retry bounded 429 responses after Retry-After."""
    response = session.get(url, headers=headers, params=params)
    retries_used = 0
    sleep = sleeper or time.sleep

    while response.status_code == 429 and retries_used < max_retries:
        sleep(parse_retry_after(response.headers))
        retries_used += 1
        response = session.get(url, headers=headers, params=params)

    response.raise_for_status()
    return response
