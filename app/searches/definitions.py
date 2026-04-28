from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class SearchFilters:
    """Hard filters and legacy keyword gates for a saved search."""

    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    item_location: Optional[str] = "GB"
    condition: Optional[str] = None
    buying_options: str = "FIXED_PRICE|AUCTION"
    required_keywords: Optional[str] = None
    excluded_keywords: Optional[str] = None


@dataclass(frozen=True)
class SearchSchedule:
    """Scheduling state for recurring search execution."""

    check_interval: int = 5
    first_run: bool = True
    last_full_run: Optional[datetime] = None
    next_full_run: Optional[datetime] = None
    last_recent_run: Optional[datetime] = None


@dataclass(frozen=True)
class SavedSearch:
    """Domain representation of a user's saved eBay search."""

    id: str
    user_id: int
    keyword_id: int
    keywords: str
    marketplace: str
    is_active: bool
    filters: SearchFilters
    schedule: SearchSchedule
