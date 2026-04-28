"""Helpers for extracting eBay analytics rate-limit data."""

from collections.abc import Mapping, Sequence
from typing import Any

RateLimitPayload = Mapping[str, Any]
RateLimitRecord = dict[str, Any]


def extract_browse_rate(rate_data: RateLimitPayload) -> RateLimitRecord:
    """Return the first buy Browse API rate-limit record.

    eBay nests Browse limits under:
    rateLimits -> buy/Browse group -> buy.browse resource -> rates[0].
    Return an empty dict when any part of that path is missing.
    """
    browse_group = _find_browse_group(rate_data)
    if browse_group is None:
        return {}

    browse_resource = _find_browse_resource(browse_group)
    if browse_resource is None:
        return {}

    return _first_rate(browse_resource)


def _find_browse_group(rate_data: RateLimitPayload) -> Mapping[str, Any] | None:
    """Find the top-level buy Browse API group."""
    for group in _mapping_sequence(rate_data.get("rateLimits")):
        if group.get("apiContext") == "buy" and group.get("apiName") == "Browse":
            return group
    return None


def _find_browse_resource(group: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Find the nested buy.browse resource."""
    for resource in _mapping_sequence(group.get("resources")):
        if resource.get("name") == "buy.browse":
            return resource
    return None


def _first_rate(resource: Mapping[str, Any]) -> RateLimitRecord:
    """Return the first rate record from a resource."""
    rates = _mapping_sequence(resource.get("rates"))
    if not rates:
        return {}
    return dict(rates[0])


def _mapping_sequence(value: Any) -> list[Mapping[str, Any]]:
    """Return only mapping entries from a sequence-like value."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item for item in value if isinstance(item, Mapping)]
