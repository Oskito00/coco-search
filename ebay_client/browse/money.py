"""Money parsing helpers for eBay Browse responses."""

from typing import Any, Mapping

Money = dict[str, float | str]


def parse_money(
    money_data: Mapping[str, Any] | None,
    default_currency: str,
) -> Money:
    """Return a normalized money dictionary with a float value and currency."""
    money_data = money_data or {}

    return {
        "value": _parse_float(money_data.get("value")),
        "currency": str(money_data.get("currency") or default_currency),
    }


def _parse_float(value: Any) -> float:
    """Convert an eBay numeric value to a float, defaulting blank values to 0."""
    if value in (None, ""):
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
