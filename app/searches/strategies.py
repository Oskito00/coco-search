"""Scrape strategies: cheap recent pass vs. full catalogue refresh.

Each strategy encapsulates the eBay sort order and pagination depth that
distinguishes its purpose. ``ScheduledQueryService`` consumes these via the
``ScrapeStrategy`` protocol so the scheduler stays agnostic of search shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from app.searches.definitions import SavedSearch
from app.searches.execution import EbaySearchExecutor


class ScrapeKind(str, Enum):
    """Identifies the purpose of a scrape pass."""

    RECENT = "recent"
    FULL = "full"


@dataclass(frozen=True)
class ScrapeOutcome:
    """Result of a single scrape execution."""

    items: list[dict[str, Any]]
    kind: ScrapeKind


class ScrapeStrategy(Protocol):
    """Pluggable scrape pass for a saved search."""

    kind: ScrapeKind

    def execute(self, saved_search: SavedSearch) -> ScrapeOutcome:
        """Return the items returned by eBay for this strategy."""


@dataclass
class RecentScrapeStrategy:
    """Cheap pass that captures newly-listed items via a single page sorted by recency."""

    kind: ScrapeKind = field(default=ScrapeKind.RECENT, init=False)
    executor: EbaySearchExecutor = field(default_factory=EbaySearchExecutor)
    sort_order: str = "newlyListed"
    max_pages: int = 1

    def execute(self, saved_search: SavedSearch) -> ScrapeOutcome:
        items = self.executor.execute_saved_search(
            saved_search,
            sort_order=self.sort_order,
            max_pages=self.max_pages,
        )
        return ScrapeOutcome(items=items, kind=self.kind)


@dataclass
class FullScrapeStrategy:
    """Catalogue refresh used to surface price drops and state changes on known items."""

    kind: ScrapeKind = field(default=ScrapeKind.FULL, init=False)
    executor: EbaySearchExecutor = field(default_factory=EbaySearchExecutor)
    sort_order: str | None = None  # None -> eBay default (bestMatch)
    max_pages: int = 5

    def execute(self, saved_search: SavedSearch) -> ScrapeOutcome:
        items = self.executor.execute_saved_search(
            saved_search,
            sort_order=self.sort_order,
            max_pages=self.max_pages,
        )
        return ScrapeOutcome(items=items, kind=self.kind)
