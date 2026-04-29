"""Feature extractors for the relevance layer.

Two flavours:

* ``item`` and ``search`` — *raw* features (the building blocks the future
  scorer will compose).
* ``legacy`` — the existing combined extractor used by the in-tree heuristic
  ``BaselineRelevanceScorer``. Kept for backwards compatibility with that
  scorer; new work should consume the raw extractors directly.
"""

from app.relevance.features.item import RAW_ITEM_FEATURE_KEYS, extract_raw_item_features
from app.relevance.features.legacy import (
    extract_item_features,
    keyword_list,
    terms,
)
from app.relevance.features.search import (
    RAW_SEARCH_FEATURE_KEYS,
    extract_raw_search_features,
)

__all__ = [
    "RAW_ITEM_FEATURE_KEYS",
    "RAW_SEARCH_FEATURE_KEYS",
    "extract_item_features",
    "extract_raw_item_features",
    "extract_raw_search_features",
    "keyword_list",
    "terms",
]
