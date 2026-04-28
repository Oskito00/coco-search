from typing import Optional

import pytest

from ebay_client.browse.dto import SearchFilters
from ebay_client.browse.filters import SearchFilterBuilder, build_search_filter


@pytest.fixture
def builder() -> SearchFilterBuilder:
    return SearchFilterBuilder("GBP")


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("NEW", "itemLocationCountry:GB,conditions:{NEW}"),
        ("USED", "itemLocationCountry:GB,conditions:{USED}"),
        ("", "itemLocationCountry:GB"),
        ("RENEWED", "itemLocationCountry:GB"),
    ],
)
def test_condition_filters(
    builder: SearchFilterBuilder, condition: str, expected: str
) -> None:
    filters = SearchFilters(condition=condition)

    assert builder.build(filters) == expected


@pytest.mark.parametrize(
    ("buying_options", "expected"),
    [
        ("FIXED_PRICE|AUCTION", "itemLocationCountry:GB"),
        ("FIXED_PRICE", "itemLocationCountry:GB,buyingOptions:{FIXED_PRICE}"),
        ("AUCTION", "itemLocationCountry:GB,buyingOptions:{AUCTION}"),
    ],
)
def test_buying_options_filters(
    builder: SearchFilterBuilder, buying_options: str, expected: str
) -> None:
    filters = SearchFilters(buying_options=buying_options)

    assert builder.build(filters) == expected


@pytest.mark.parametrize(
    ("item_location", "expected"),
    [
        ("GB", "itemLocationCountry:GB"),
        ("US", "itemLocationCountry:US"),
        ("any", ""),
        (None, ""),
    ],
)
def test_location_filters(
    builder: SearchFilterBuilder, item_location: Optional[str], expected: str
) -> None:
    filters = SearchFilters(item_location=item_location)

    assert builder.build(filters) == expected


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        (
            SearchFilters(min_price=10, max_price=50, item_location="any"),
            "priceCurrency:GBP,price:[10..50]",
        ),
        (
            SearchFilters(min_price=10, item_location="any"),
            "priceCurrency:GBP,price:[10..]",
        ),
        (
            SearchFilters(max_price=50, item_location="any"),
            "priceCurrency:GBP,price:[..50]",
        ),
        (
            SearchFilters(min_price=0, item_location="any"),
            "price:[0..]",
        ),
    ],
)
def test_price_range_filters(
    builder: SearchFilterBuilder, filters: SearchFilters, expected: str
) -> None:
    assert builder.build(filters) == expected


def test_dict_and_search_filters_input_build_same_filter() -> None:
    mapping_filters = {
        "min_price": 10,
        "max_price": 20,
        "item_location": "US",
        "condition": "USED",
        "buying_options": "AUCTION",
    }
    search_filters = SearchFilters(
        min_price=10,
        max_price=20,
        item_location="US",
        condition="USED",
        buying_options="AUCTION",
    )

    assert build_search_filter(mapping_filters, "USD") == build_search_filter(
        search_filters, "USD"
    )
