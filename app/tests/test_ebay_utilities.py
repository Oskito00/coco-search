from datetime import datetime, timezone
from typing import Any

import pytest

from ebay_client.browse.responses import dedupe_items
from ebay_client.time import parse_ebay_datetime


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "2026-04-28T15:30:45.123Z",
            datetime(2026, 4, 28, 15, 30, 45, 123000, tzinfo=timezone.utc),
        ),
        (
            "2026-04-28T15:30:45+00:00",
            datetime(2026, 4, 28, 15, 30, 45, tzinfo=timezone.utc),
        ),
        (
            "2026-04-28T16:30:45+01:00",
            datetime(2026, 4, 28, 15, 30, 45, tzinfo=timezone.utc),
        ),
    ],
)
def test_parse_ebay_datetime_supported_formats(
    value: str,
    expected: datetime,
) -> None:
    assert parse_ebay_datetime(value) == expected


@pytest.mark.parametrize("value", [None, "", "not-a-date"])
def test_parse_ebay_datetime_invalid_values(value: str | None) -> None:
    assert parse_ebay_datetime(value) is None


def test_dedupe_items_removes_duplicate_ebay_ids() -> None:
    first_item = {"ebay_id": "v1|123", "title": "first"}
    duplicate_item = {"ebay_id": "v1|123", "title": "duplicate"}
    second_item = {"ebay_id": "v1|456", "title": "second"}

    assert dedupe_items([first_item, duplicate_item, second_item]) == [
        first_item,
        second_item,
    ]


def test_dedupe_items_keeps_items_without_ebay_id() -> None:
    items: list[dict[str, Any]] = [
        {"title": "missing id"},
        {"ebay_id": None, "title": "none id"},
        {"ebay_id": "", "title": "empty id"},
        {"title": "another missing id"},
    ]

    assert dedupe_items(items) == items
