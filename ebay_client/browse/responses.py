from typing import Any


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate items that have the same eBay item identifier."""
    seen_ids: set[Any] = set()
    unique_items: list[dict[str, Any]] = []

    for item in items:
        item_id = _dedupe_key(item)
        if _should_keep_item(item_id, seen_ids):
            _remember_item_id(item_id, seen_ids)
            unique_items.append(item)

    return unique_items


def _dedupe_key(item: dict[str, Any]) -> Any:
    """Return the identifier used to dedupe an item."""
    return item.get("ebay_id")


def _should_keep_item(item_id: Any, seen_ids: set[Any]) -> bool:
    """Return whether an item should remain in the result list."""
    return not item_id or item_id not in seen_ids


def _remember_item_id(item_id: Any, seen_ids: set[Any]) -> None:
    """Remember an item identifier when it participates in deduping."""
    if item_id:
        seen_ids.add(item_id)
