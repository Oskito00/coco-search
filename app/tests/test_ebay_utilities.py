from datetime import datetime, timezone

import pytest

from ebay_client.browse.responses import dedupe_items
from ebay_client.time import parse_ebay_datetime


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "2026-04-28T13:45:10.000Z",
            datetime(2026, 4, 28, 13, 45, 10, tzinfo=timezone.utc),
        ),
        (
            "2026-04-28T13:45:10Z",
            datetime(2026, 4, 28, 13, 45, 10, tzinfo=timezone.utc),
        ),
        (
            "2026-04-28T14:45:10+01:00",
            datetime.fromisoformat("2026-04-28T14:45:10+01:00"),
        ),
    ],
)
def test_parse_ebay_datetime_supported_formats(
    value: str,
    expected: datetime,
) -> None:
    assert parse_ebay_datetime(value) == expected


@pytest.mark.parametrize("value", [None, "", "not-a-date", "2026-99-99T00:00:00Z"])
def test_parse_ebay_datetime_invalid_or_missing_values(
    value: str | None,
) -> None:
    assert parse_ebay_datetime(value) is None


def test_dedupe_items_preserves_first_id_match_and_items_without_ids() -> None:
    first = {"ebay_id": "1", "title": "first"}
    duplicate = {"ebay_id": "1", "title": "duplicate"}
    no_id = {"title": "no id"}
    empty_id = {"ebay_id": "", "title": "empty id"}
    second = {"ebay_id": "2", "title": "second"}

    assert dedupe_items([first, duplicate, no_id, empty_id, second]) == [
        first,
        no_id,
        empty_id,
        second,
    ]


def test_dedupe_items_accepts_any_iterable() -> None:
    items = (
        {"ebay_id": str(item_id), "title": f"item {item_id}"} for item_id in [1, 1, 2]
    )

    assert [item["ebay_id"] for item in dedupe_items(items)] == ["1", "2"]
