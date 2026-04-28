from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.searches.definitions import SavedSearch, SearchFilters, SearchSchedule
from app.searches.mapping import saved_search_from_model, to_ebay_search_params
from app.searches.validation import SearchValidationError, ensure_valid_saved_search


@dataclass
class KeywordStub:
    keyword_text: str


@dataclass
class UserQueryStub:
    query_id: str
    user_id: int
    keyword_id: int
    keyword: KeywordStub
    marketplace: str
    is_active: bool
    min_price: Decimal | None
    max_price: Decimal | None
    item_location: str
    condition: str
    buying_options: str
    required_keywords: str
    excluded_keywords: str
    check_interval: int
    first_run: bool
    last_full_run: datetime | None
    next_full_run: datetime | None
    last_recent_run: datetime | None


def test_saved_search_from_model_maps_query_fields() -> None:
    last_full_run = datetime(2026, 4, 28, tzinfo=timezone.utc)
    query = UserQueryStub(
        query_id="search-1",
        user_id=7,
        keyword_id=11,
        keyword=KeywordStub(keyword_text="sony camera"),
        marketplace="EBAY_GB",
        is_active=True,
        min_price=Decimal("10.50"),
        max_price=Decimal("250.00"),
        item_location="GB",
        condition="USED",
        buying_options="AUCTION",
        required_keywords="sony",
        excluded_keywords="broken",
        check_interval=15,
        first_run=False,
        last_full_run=last_full_run,
        next_full_run=None,
        last_recent_run=None,
    )

    saved_search = saved_search_from_model(query)

    assert saved_search == SavedSearch(
        id="search-1",
        user_id=7,
        keyword_id=11,
        keywords="sony camera",
        marketplace="EBAY_GB",
        is_active=True,
        filters=SearchFilters(
            min_price=Decimal("10.50"),
            max_price=Decimal("250.00"),
            item_location="GB",
            condition="USED",
            buying_options="AUCTION",
            required_keywords="sony",
            excluded_keywords="broken",
        ),
        schedule=SearchSchedule(
            check_interval=15,
            first_run=False,
            last_full_run=last_full_run,
            next_full_run=None,
            last_recent_run=None,
        ),
    )


def test_to_ebay_search_params_uses_sdk_filter_shape() -> None:
    saved_search = SavedSearch(
        id="search-1",
        user_id=7,
        keyword_id=11,
        keywords="sony camera",
        marketplace="EBAY_GB",
        is_active=True,
        filters=SearchFilters(
            min_price=Decimal("10.50"),
            max_price=Decimal("250.00"),
            item_location="GB",
            condition="USED",
            buying_options="AUCTION",
            required_keywords="sony",
            excluded_keywords="broken",
        ),
        schedule=SearchSchedule(check_interval=5),
    )

    params = to_ebay_search_params(saved_search)

    assert params == {
        "keywords": "sony camera",
        "filters": {
            "min_price": 10.5,
            "max_price": 250.0,
            "item_location": "GB",
            "condition": "USED",
            "buying_options": "AUCTION",
        },
        "marketplace": "EBAY_GB",
    }


def test_validation_rejects_intervals_below_five_minutes() -> None:
    saved_search = SavedSearch(
        id="search-1",
        user_id=7,
        keyword_id=11,
        keywords="sony camera",
        marketplace="EBAY_GB",
        is_active=True,
        filters=SearchFilters(),
        schedule=SearchSchedule(check_interval=4),
    )

    with pytest.raises(SearchValidationError) as exc_info:
        ensure_valid_saved_search(saved_search)

    assert "schedule.check_interval: must be at least 5 minutes" in str(exc_info.value)
