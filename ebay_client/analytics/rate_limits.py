from typing import Any


def extract_browse_rate(rate_data: dict[str, Any] | None) -> dict[str, Any]:
    """Return the first Browse API rate limit entry from eBay analytics data."""
    for limit in _browse_limits(rate_data):
        rate = _extract_browse_resource_rate(limit)
        if rate is not None:
            return rate
    return {}


def _browse_limits(rate_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return rate limit groups for the Buy Browse API."""
    if not rate_data:
        return []

    return [
        limit for limit in rate_data.get("rateLimits", []) if _is_browse_limit(limit)
    ]


def _is_browse_limit(limit: dict[str, Any]) -> bool:
    """Return whether a rate limit group describes the Buy Browse API."""
    return limit.get("apiContext") == "buy" and limit.get("apiName") == "Browse"


def _extract_browse_resource_rate(limit: dict[str, Any]) -> dict[str, Any] | None:
    """Return the first rate entry for the buy.browse resource."""
    for resource in _browse_resources(limit):
        return _first_rate(resource)
    return None


def _browse_resources(limit: dict[str, Any]) -> list[dict[str, Any]]:
    """Return resources that represent the Browse API."""
    return [
        resource
        for resource in limit.get("resources", [])
        if resource.get("name") == "buy.browse"
    ]


def _first_rate(resource: dict[str, Any]) -> dict[str, Any] | None:
    """Return the first rate for a resource, or None when missing."""
    rates = resource.get("rates", [])
    if not rates:
        return None
    return rates[0]
