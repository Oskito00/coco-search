from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SearchFilters:
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    item_location: Optional[str] = "GB"
    condition: Optional[str] = None
    buying_options: str = "FIXED_PRICE|AUCTION"

    @classmethod
    def from_mapping(cls, filters):
        filters = filters or {}
        return cls(
            min_price=filters.get("min_price"),
            max_price=filters.get("max_price"),
            item_location=filters.get("item_location"),
            condition=filters.get("condition"),
            buying_options=filters.get("buying_options", "FIXED_PRICE|AUCTION"),
        )


@dataclass(frozen=True)
class SearchRequest:
    keywords: str
    filters: SearchFilters
    limit: int = 200
    offset: int = 0
    sort_order: Optional[str] = None
