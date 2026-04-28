"""Response helpers for eBay Browse API data."""

from collections.abc import Iterable, Mapping, MutableMapping
from typing import Any, TypeVar

Item = TypeVar("Item", bound=MutableMapping[str, Any])


def dedupe_items(items: Iterable[Item]) -> list[Item]:
    """Remove duplicate items by ``ebay_id`` while preserving order.

    Items without an ``ebay_id`` are always preserved.
    """
    seen_ids: set[Any] = set()
    unique_items: list[Item] = []

    for item in items:
        if _should_keep_item(item, seen_ids):
            unique_items.append(item)

    return unique_items


def _should_keep_item(item: Mapping[str, Any], seen_ids: set[Any]) -> bool:
    """Return whether an item should be included in the de-duped output."""
    ebay_id = item.get("ebay_id")
    if not ebay_id:
        return True
    if ebay_id in seen_ids:
        return False

    seen_ids.add(ebay_id)
    return True
