from decimal import Decimal
from types import SimpleNamespace

from app.routes import queries
from app.searches import saved_search_from_model, to_ebay_search_params


def _saved_search_model(**overrides):
    values = {
        "query_id": "query-1",
        "user_id": 12,
        "keyword_id": 34,
        "keyword": SimpleNamespace(keyword_text="Sony Camera"),
        "marketplace": "EBAY_GB",
        "is_active": True,
        "min_price": Decimal("10.00"),
        "max_price": Decimal("200.00"),
        "item_location": "any",
        "condition": "",
        "buying_options": "FIXED_PRICE|AUCTION",
        "required_keywords": "sony",
        "excluded_keywords": "charger",
        "check_interval": 15,
        "first_run": True,
        "last_full_run": None,
        "next_full_run": None,
        "last_recent_run": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_saved_search_from_model_preserves_legacy_keyword_filters():
    saved_search = saved_search_from_model(_saved_search_model())

    assert saved_search.id == "query-1"
    assert saved_search.keywords == "Sony Camera"
    assert saved_search.filters.item_location == "any"
    assert saved_search.filters.required_keywords == "sony"
    assert saved_search.filters.excluded_keywords == "charger"
    assert saved_search.schedule.check_interval == 15


def test_to_ebay_search_params_uses_shared_sdk_filter_shape():
    saved_search = saved_search_from_model(
        _saved_search_model(max_price=None, condition=None, item_location="GB")
    )

    params = to_ebay_search_params(saved_search)

    assert params["keywords"] == "Sony Camera"
    assert params["marketplace"] == "EBAY_GB"
    assert params["filters"] == {
        "min_price": 10.0,
        "max_price": None,
        "item_location": "GB",
        "condition": None,
        "buying_options": "FIXED_PRICE|AUCTION",
    }


def test_item_matches_saved_search_keeps_hard_filters_required():
    saved_search = saved_search_from_model(_saved_search_model(item_location="GB"))
    matching_item = SimpleNamespace(
        title="Sony mirrorless camera body",
        location_country="GB",
        marketplace="EBAY_GB",
    )
    excluded_item = SimpleNamespace(
        title="Sony camera charger",
        location_country="GB",
        marketplace="EBAY_GB",
    )
    wrong_marketplace_item = SimpleNamespace(
        title="Sony mirrorless camera body",
        location_country="GB",
        marketplace="EBAY_US",
    )

    assert queries._item_matches_saved_search(matching_item, saved_search) is True
    assert queries._item_matches_saved_search(excluded_item, saved_search) is False
    assert (
        queries._item_matches_saved_search(wrong_marketplace_item, saved_search)
        is False
    )


def test_item_matches_saved_search_treats_any_location_as_unconstrained():
    saved_search = saved_search_from_model(_saved_search_model(item_location="any"))
    matching_item = SimpleNamespace(
        title="Sony mirrorless camera body",
        location_country="US",
        marketplace="EBAY_GB",
    )

    assert queries._item_matches_saved_search(matching_item, saved_search) is True
