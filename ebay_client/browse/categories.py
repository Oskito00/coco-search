"""Category serialization helpers for eBay Browse responses."""

import json
from typing import Any, Mapping, Sequence


def serialize_categories(categories: Sequence[Mapping[str, Any]] | None) -> str:
    """Serialize eBay category data in the shape expected by item callers."""
    categories = categories or []

    return json.dumps(
        {
            "ids": [category.get("categoryId") for category in categories],
            "names": [category.get("categoryName") for category in categories],
        }
    )
