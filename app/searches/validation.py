from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.searches.definitions import SavedSearch, SearchFilters, SearchSchedule

MIN_CHECK_INTERVAL_MINUTES = 5


@dataclass(frozen=True)
class ValidationIssue:
    """A structured validation failure for search-domain objects."""

    field: str
    message: str


class SearchValidationError(ValueError):
    """Raised when a search-domain object fails validation."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        message = "; ".join(f"{issue.field}: {issue.message}" for issue in issues)
        super().__init__(message)


def validate_search_schedule(schedule: SearchSchedule) -> list[ValidationIssue]:
    """Return validation issues for a search schedule."""

    issues: list[ValidationIssue] = []
    if schedule.check_interval < MIN_CHECK_INTERVAL_MINUTES:
        issues.append(
            ValidationIssue(
                field="schedule.check_interval",
                message="must be at least 5 minutes",
            )
        )
    return issues


def validate_search_filters(filters: SearchFilters) -> list[ValidationIssue]:
    """Return validation issues for search filters."""

    issues: list[ValidationIssue] = []
    if (
        filters.min_price is not None
        and filters.max_price is not None
        and Decimal(filters.min_price) > Decimal(filters.max_price)
    ):
        issues.append(
            ValidationIssue(
                field="filters.max_price",
                message="must be greater than or equal to min_price",
            )
        )
    return issues


def validate_saved_search(saved_search: SavedSearch) -> list[ValidationIssue]:
    """Return validation issues for a saved search."""

    issues = []
    if not saved_search.keywords.strip():
        issues.append(ValidationIssue(field="keywords", message="must not be blank"))
    if not saved_search.marketplace.strip():
        issues.append(ValidationIssue(field="marketplace", message="must not be blank"))

    issues.extend(validate_search_filters(saved_search.filters))
    issues.extend(validate_search_schedule(saved_search.schedule))
    return issues


def ensure_valid_saved_search(saved_search: SavedSearch) -> None:
    """Raise SearchValidationError when a saved search is invalid."""

    issues = validate_saved_search(saved_search)
    if issues:
        raise SearchValidationError(issues)
