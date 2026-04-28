from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any, Optional

NEAR_DUPLICATE_THRESHOLD = 0.86


def diverse_items(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Select diverse items while avoiding near-duplicate titles."""

    if limit <= 0:
        return []

    selected: list[dict[str, Any]] = []
    remaining = list(items)
    price_bands = _price_bands(items)

    while remaining and len(selected) < limit:
        best = _best_candidate(remaining, selected, price_bands)
        if best is None:
            break
        selected.append(best)
        remaining.remove(best)

    return selected


def _best_candidate(
    candidates: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    price_bands: dict[int, str],
) -> Optional[dict[str, Any]]:
    selected_titles = [_normalized_title(item) for item in selected]
    selectable = [
        item
        for item in candidates
        if not _is_near_duplicate(_normalized_title(item), selected_titles)
    ]
    if not selectable:
        return None

    condition_counts = Counter(_condition(item) for item in selected)
    location_counts = Counter(_location(item) for item in selected)
    price_band_counts = Counter(_price_band(item, price_bands) for item in selected)

    return max(
        selectable,
        key=lambda item: (
            _rarity_score(_condition(item), condition_counts),
            _rarity_score(_location(item), location_counts),
            _rarity_score(_price_band(item, price_bands), price_band_counts),
            -candidates.index(item),
        ),
    )


def _rarity_score(value: str, counts: Counter[str]) -> int:
    if value == "unknown":
        return 0
    return -counts[value]


def _normalized_title(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").lower()
    return re.sub(r"\W+", " ", title).strip()


def _is_near_duplicate(title: str, selected_titles: list[str]) -> bool:
    if not title:
        return False
    return any(
        SequenceMatcher(None, title, selected_title).ratio() >= NEAR_DUPLICATE_THRESHOLD
        for selected_title in selected_titles
    )


def _condition(item: dict[str, Any]) -> str:
    return str(item.get("condition") or "unknown").lower()


def _location(item: dict[str, Any]) -> str:
    location = item.get("location")
    if isinstance(location, dict):
        return str(location.get("country") or "unknown").lower()
    return str(location or item.get("item_location") or "unknown").lower()


def _price_band(item: dict[str, Any], price_bands: dict[int, str]) -> str:
    return price_bands.get(id(item), "unknown")


def _price_bands(items: list[dict[str, Any]]) -> dict[int, str]:
    prices = sorted(
        price for price in (_price(item) for item in items) if price is not None
    )
    if not prices:
        return {}

    low_cutoff = prices[len(prices) // 3]
    high_cutoff = prices[(len(prices) * 2) // 3]
    bands = {}
    for item in items:
        price = _price(item)
        if price is None:
            bands[id(item)] = "unknown"
        elif price <= low_cutoff:
            bands[id(item)] = "low"
        elif price <= high_cutoff:
            bands[id(item)] = "mid"
        else:
            bands[id(item)] = "high"
    return bands


def _price(item: dict[str, Any]) -> Optional[Decimal]:
    value = item.get("price")
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return Decimal(str(value)) if value not in (None, "") else None
    except (InvalidOperation, TypeError):
        return None
