from ebay_client.browse.dto import SearchFilters
from ebay_client.browse.filters import SearchFilterBuilder, build_search_filter


def test_condition_filters_include_only_supported_conditions():
    builder = SearchFilterBuilder("GBP")

    assert "conditions" not in builder.build({"condition": ""})
    assert builder.build({"condition": "NEW"}) == "conditions:{NEW}"
    assert builder.build({"condition": "USED"}) == "conditions:{USED}"
    assert "conditions" not in builder.build({"condition": "RENEWED"})


def test_buying_options_filters_skip_any_and_include_specific_options():
    builder = SearchFilterBuilder("GBP")

    assert builder.build({"buying_options": "FIXED_PRICE|AUCTION"}) == ""
    assert builder.build({"buying_options": "any"}) == ""
    assert builder.build({"buying_options": "FIXED_PRICE"}) == (
        "buyingOptions:{FIXED_PRICE}"
    )
    assert builder.build({"buying_options": "AUCTION"}) == "buyingOptions:{AUCTION}"


def test_location_filter_skips_any_and_includes_specific_country():
    builder = SearchFilterBuilder("GBP")

    assert builder.build({"item_location": "any"}) == ""
    assert builder.build({"item_location": "GB"}) == "itemLocationCountry:GB"


def test_price_range_filters_include_currency_and_requested_bounds():
    builder = SearchFilterBuilder("GBP")

    assert builder.build({"min_price": 10}) == "priceCurrency:GBP,price:[10..]"
    assert builder.build({"max_price": 50}) == "priceCurrency:GBP,price:[..50]"
    assert builder.build({"min_price": 10, "max_price": 50}) == (
        "priceCurrency:GBP,price:[10..50]"
    )


def test_dict_and_search_filters_input_build_identical_filter_strings():
    filters_dict = {
        "item_location": "US",
        "buying_options": "AUCTION",
        "condition": "USED",
        "min_price": 25,
        "max_price": 75,
    }
    search_filters = SearchFilters(
        item_location="US",
        buying_options="AUCTION",
        condition="USED",
        min_price=25,
        max_price=75,
    )

    assert build_search_filter(filters_dict, "USD") == build_search_filter(
        search_filters, "USD"
    )
    assert build_search_filter(search_filters, "USD") == (
        "itemLocationCountry:US,buyingOptions:{AUCTION},"
        "conditions:{USED},priceCurrency:USD,price:[25..75]"
    )
