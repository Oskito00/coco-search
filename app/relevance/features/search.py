"""Raw, search-only feature extraction (no item context).

Mirror of :mod:`app.relevance.features.item` for the saved-search side. The
output is a flat, JSON-safe dict ready to be serialized into
:class:`ItemFeatureSnapshot`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

RAW_SEARCH_FEATURE_KEYS: tuple[str, ...] = (
    "keywords",
    "min_price",
    "max_price",
    "condition_filter",
    "location_filter",
    "buying_options_filter",
    "required_keywords",
    "excluded_keywords",
    "marketplace",
    "check_interval",
)


def extract_raw_search_features(saved_search: Any) -> dict[str, Any]:
    """Return a flat dict of raw saved-search features."""
    filters = _attr(saved_search, "filters") or {}
    schedule = _attr(saved_search, "schedule") or {}

    return {
        "keywords": _str(_keywords(saved_search)),
        "min_price": _float_or_none(_filter(saved_search, filters, "min_price")),
        "max_price": _float_or_none(_filter(saved_search, filters, "max_price")),
        "condition_filter": _attr_or_filter(saved_search, filters, "condition"),
        "location_filter": _attr_or_filter(saved_search, filters, "item_location"),
        "buying_options_filter": _attr_or_filter(
            saved_search, filters, "buying_options"
        ),
        "required_keywords": _attr_or_filter(
            saved_search, filters, "required_keywords"
        ),
        "excluded_keywords": _attr_or_filter(
            saved_search, filters, "excluded_keywords"
        ),
        "marketplace": _attr(saved_search, "marketplace"),
        "check_interval": _int_or_none(
            _attr(schedule, "check_interval")
            if schedule
            else _attr(saved_search, "check_interval")
        ),
    }


def _keywords(saved_search: Any) -> Optional[str]:
    keywords = _attr(saved_search, "keywords")
    if keywords:
        return str(keywords)
    keyword = _attr(saved_search, "keyword")
    text = _attr(keyword, "keyword_text") if keyword is not None else None
    return _str(text)


def _attr_or_filter(saved_search: Any, filters: Any, name: str) -> Any:
    value = _attr(filters, name)
    if value is not None:
        return value
    return _attr(saved_search, name)


def _filter(saved_search: Any, filters: Any, name: str) -> Any:
    return _attr_or_filter(saved_search, filters, name)


def _attr(source: Any, name: str) -> Any:
    if source is None:
        return None
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _float_or_none(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
