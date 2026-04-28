from __future__ import annotations

from typing import Any, Mapping, Optional, Union

from ebay_client.browse.dto import SearchFilters

DEFAULT_BUYING_OPTIONS = "FIXED_PRICE|AUCTION"
VALID_CONDITIONS = {"NEW", "USED"}
SearchFilterInput = Union[SearchFilters, Mapping[str, Any]]


class SearchFilterBuilder:
    """Build eBay Browse API filter strings from search filters."""

    def __init__(self, currency: str) -> None:
        self.currency = currency

    def build(self, filters: SearchFilterInput) -> str:
        """Return the eBay Browse API filter string for the given filters."""
        search_filters = self._normalize_filters(filters)
        filter_parts = [
            self._location_filter(search_filters),
            self._buying_options_filter(search_filters),
            self._condition_filter(search_filters),
            self._currency_filter(search_filters),
            self._price_range_filter(search_filters),
        ]

        return ",".join(filter_part for filter_part in filter_parts if filter_part)

    def _normalize_filters(self, filters: SearchFilterInput) -> SearchFilters:
        if isinstance(filters, Mapping):
            return SearchFilters.from_mapping(filters)
        return filters

    def _location_filter(self, filters: SearchFilters) -> Optional[str]:
        item_location = filters.item_location
        if item_location and item_location != "any":
            return f"itemLocationCountry:{item_location}"
        return None

    def _buying_options_filter(self, filters: SearchFilters) -> Optional[str]:
        if filters.buying_options != DEFAULT_BUYING_OPTIONS:
            return f"buyingOptions:{{{filters.buying_options}}}"
        return None

    def _condition_filter(self, filters: SearchFilters) -> Optional[str]:
        if filters.condition in VALID_CONDITIONS:
            return f"conditions:{{{filters.condition}}}"
        return None

    def _currency_filter(self, filters: SearchFilters) -> Optional[str]:
        if filters.min_price or filters.max_price:
            return f"priceCurrency:{self.currency}"
        return None

    def _price_range_filter(self, filters: SearchFilters) -> Optional[str]:
        if filters.min_price is not None or filters.max_price is not None:
            return f"price:[{self._format_price_range(filters)}]"
        return None

    def _format_price_range(self, filters: SearchFilters) -> str:
        if filters.min_price is not None and filters.max_price is not None:
            return f"{filters.min_price}..{filters.max_price}"
        if filters.min_price is not None:
            return f"{filters.min_price}.."
        return f"..{filters.max_price}"


def build_search_filter(filters: SearchFilterInput, currency: str) -> str:
    """Build an eBay Browse API filter string using the given currency."""
    return SearchFilterBuilder(currency).build(filters)
