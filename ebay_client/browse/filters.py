"""Filter construction helpers for eBay Browse search requests."""

from __future__ import annotations

from .dto import SearchFilterInput, SearchFilters, normalize_search_filters

ANY_BUYING_OPTIONS = frozenset({"", "any", "ANY", "FIXED_PRICE|AUCTION"})
VALID_CONDITIONS = frozenset({"NEW", "USED"})


class SearchFilterBuilder:
    """Build eBay Browse API filter strings from search filter options."""

    def __init__(self, currency: str) -> None:
        self.currency = currency

    def build(self, filters: SearchFilterInput) -> str:
        """Build a comma-separated Browse API filter string."""
        normalized_filters = normalize_search_filters(filters)
        parts = [
            _build_location_filter(normalized_filters),
            _build_buying_options_filter(normalized_filters),
            _build_condition_filter(normalized_filters),
            _build_currency_filter(normalized_filters, self.currency),
            _build_price_range_filter(normalized_filters),
        ]

        return ",".join(part for part in parts if part is not None)


def build_search_filter(filters: SearchFilterInput, currency: str) -> str:
    """Build an eBay Browse API filter string with the default builder."""
    return SearchFilterBuilder(currency).build(filters)


def _build_location_filter(filters: SearchFilters) -> str | None:
    location = filters.item_location
    if location and location != "any":
        return f"itemLocationCountry:{location}"

    return None


def _build_buying_options_filter(filters: SearchFilters) -> str | None:
    buying_options = filters.buying_options or "FIXED_PRICE|AUCTION"
    if buying_options in ANY_BUYING_OPTIONS:
        return None

    return f"buyingOptions:{{{buying_options}}}"


def _build_condition_filter(filters: SearchFilters) -> str | None:
    condition = filters.condition
    if condition in VALID_CONDITIONS:
        return f"conditions:{{{condition}}}"

    return None


def _build_currency_filter(filters: SearchFilters, currency: str) -> str | None:
    if _has_price_range(filters):
        return f"priceCurrency:{currency}"

    return None


def _build_price_range_filter(filters: SearchFilters) -> str | None:
    min_price = filters.min_price
    max_price = filters.max_price

    if min_price is not None and max_price is not None:
        return f"price:[{min_price}..{max_price}]"

    if min_price is not None:
        return f"price:[{min_price}..]"

    if max_price is not None:
        return f"price:[..{max_price}]"

    return None


def _has_price_range(filters: SearchFilters) -> bool:
    return filters.min_price is not None or filters.max_price is not None
