"""Data transfer objects for eBay Browse API requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, TypeAlias

PriceBound: TypeAlias = int | float | str
SearchFilterInput: TypeAlias = "SearchFilters | Mapping[str, object] | None"


@dataclass(frozen=True)
class SearchFilters:
    """Normalized eBay Browse search filter options."""

    item_location: str | None = None
    buying_options: str | None = None
    condition: str | None = None
    min_price: PriceBound | None = None
    max_price: PriceBound | None = None

    @classmethod
    def from_mapping(cls, filters: Mapping[str, object] | None) -> "SearchFilters":
        """Create search filters from a mapping, ignoring unknown keys."""
        if filters is None:
            return cls()

        return cls(
            item_location=_optional_string(filters.get("item_location")),
            buying_options=_optional_string(filters.get("buying_options")),
            condition=_optional_string(filters.get("condition")),
            min_price=_optional_price_bound(filters.get("min_price")),
            max_price=_optional_price_bound(filters.get("max_price")),
        )


def normalize_search_filters(filters: SearchFilterInput) -> SearchFilters:
    """Return a SearchFilters instance for dataclass, mapping, or empty input."""
    if isinstance(filters, SearchFilters):
        return filters

    return SearchFilters.from_mapping(filters)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None

    return str(value)


def _optional_price_bound(value: object) -> PriceBound | None:
    if value is None:
        return None

    if isinstance(value, (int, float, str)):
        return value

    return str(value)
