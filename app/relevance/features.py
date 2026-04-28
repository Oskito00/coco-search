import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from app.utils.text_helpers import remove_accents

ACCESSORY_TERMS = {
    "case",
    "cases",
    "cover",
    "covers",
    "protector",
    "screen",
    "charger",
    "cable",
    "mount",
    "holder",
}


def extract_item_features(saved_search: Any, item: Any) -> dict[str, Any]:
    """Extract reusable search and item features for relevance decisions."""

    query_text = _query_text(saved_search)
    title = _string_value(_value(item, "title"))
    description = _string_value(_value(item, "description"))
    title_terms = terms(title)
    query_terms = terms(query_text)
    required_keywords = keyword_list(_filter_value(saved_search, "required_keywords"))
    excluded_keywords = keyword_list(_filter_value(saved_search, "excluded_keywords"))
    item_text = f"{title} {description}".strip()

    return {
        "saved_search_id": _string_value(
            _value(saved_search, "id") or _value(saved_search, "query_id")
        ),
        "item_id": _string_value(_value(item, "item_id") or _value(item, "id")),
        "query_text": query_text,
        "title": title,
        "description": description,
        "query_terms": query_terms,
        "title_terms": title_terms,
        "required_keywords": required_keywords,
        "excluded_keywords": excluded_keywords,
        "required_keywords_present": _required_keywords_present(
            item_text, required_keywords
        ),
        "excluded_keywords_present": _excluded_keywords_present(
            item_text, excluded_keywords
        ),
        "query_term_count": len(query_terms),
        "query_term_match_count": len(query_terms & title_terms),
        "query_match_ratio": _query_match_ratio(query_terms, title_terms),
        "accessory_terms_present": bool(ACCESSORY_TERMS & title_terms),
        "query_has_accessory_terms": bool(ACCESSORY_TERMS & query_terms),
        "price": _decimal_value(_value(item, "price")),
        "min_price": _decimal_value(_filter_value(saved_search, "min_price")),
        "max_price": _decimal_value(_filter_value(saved_search, "max_price")),
        "condition": _normalized_optional(_value(item, "condition")),
        "expected_condition": _normalized_optional(
            _filter_value(saved_search, "condition")
        ),
        "location_country": _normalized_optional(
            _value(item, "location_country")
            or _nested_value(item, "location", "country")
        ),
        "expected_location": _normalized_optional(
            _filter_value(saved_search, "item_location")
        ),
        "buying_options": _normalized_optional(_value(item, "buying_options")),
        "expected_buying_options": _normalized_optional(
            _filter_value(saved_search, "buying_options")
        ),
    }


def terms(text: str | None) -> set[str]:
    """Return normalized alphanumeric terms from text."""

    normalized = remove_accents((text or "").lower())
    return set(re.findall(r"[a-z0-9]+", normalized))


def keyword_list(value: Any) -> tuple[str, ...]:
    """Parse comma-separated keyword filters into normalized terms."""

    if not value:
        return ()
    return tuple(
        remove_accents(keyword.strip().lower())
        for keyword in str(value).split(",")
        if keyword.strip()
    )


def _query_text(saved_search: Any) -> str:
    keyword = _value(saved_search, "keyword")
    keyword_text = _value(keyword, "keyword_text") if keyword else None
    return _string_value(
        _value(saved_search, "keywords")
        or keyword_text
        or _value(saved_search, "keyword_text")
    )


def _filter_value(saved_search: Any, name: str) -> Any:
    filters = _value(saved_search, "filters")
    value = _value(filters, name) if filters is not None else None
    if value is not None:
        return value
    return _value(saved_search, name)


def _value(source: Any, name: str) -> Any:
    if source is None:
        return None
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _nested_value(source: Any, outer: str, inner: str) -> Any:
    nested = _value(source, outer)
    return _value(nested, inner)


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalized_optional(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    return normalized or None


def _decimal_value(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _query_match_ratio(query_terms: set[str], title_terms: set[str]) -> float:
    if not query_terms:
        return 0.5
    return len(query_terms & title_terms) / len(query_terms)


def _required_keywords_present(text: str, required_keywords: tuple[str, ...]) -> bool:
    if not required_keywords:
        return True
    normalized = remove_accents(text.lower())
    return all(keyword in normalized for keyword in required_keywords)


def _excluded_keywords_present(text: str, excluded_keywords: tuple[str, ...]) -> bool:
    if not excluded_keywords:
        return False
    normalized = remove_accents(text.lower())
    return any(keyword in normalized for keyword in excluded_keywords)
