"""HTTP transport helpers for eBay Browse API calls."""

import logging
import time
from collections.abc import Callable, Mapping
from typing import Any

import requests  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def fetch_json_with_retry(
    *,
    session: requests.Session,
    url: str,
    headers: Mapping[str, str],
    params: Mapping[str, str | int],
    max_retries: int,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Fetch JSON with bounded Retry-After handling for HTTP 429 responses."""
    response: requests.Response | None = None

    for attempt in range(max_retries + 1):
        response = session.get(url, headers=dict(headers), params=dict(params))
        if response.status_code != 429:
            response.raise_for_status()
            return response.json()

        if attempt == max_retries:
            break

        sleep_time = parse_retry_after(response.headers.get("Retry-After"))
        logger.warning(
            "eBay Browse rate limited; retrying after %s seconds", sleep_time
        )
        sleeper(sleep_time)

    if response is None:
        raise RuntimeError("Browse request did not return a response")

    response.raise_for_status()
    return response.json()


def parse_retry_after(value: str | None, default: int = 60) -> int:
    """Return a non-negative Retry-After value in seconds."""
    if value is None:
        return default

    try:
        return max(0, int(value))
    except ValueError:
        return default
